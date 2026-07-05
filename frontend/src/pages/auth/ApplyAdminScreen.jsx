import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { CheckCircle2, ShieldCheck } from "lucide-react";
import Button from "../../components/ui/Button";
import { TextInput, OtpInput } from "../../components/ui/Input";
import FileInput from "../../components/ui/FileInput";
import { applyAdmin, sendAdminOtp, verifyAdminOtp } from "../../api/applications";
import { apiErrorMessage } from "../../api/client";
import { ROUTES } from "../../constants/routes";

const emptyForm = {
  fullName: "",
  applicantEmail: "",
  designation: "",
  idCardPhotoUrl: "",
  campusName: "",
  campusLocation: "",
};

export default function ApplyAdminScreen() {
  const [step, setStep] = useState("details"); // details -> otp -> done
  const [form, setForm] = useState(emptyForm);
  const [otp, setOtp] = useState("");

  const sendOtp = useMutation({ mutationFn: sendAdminOtp });
  const verifyOtp = useMutation({ mutationFn: verifyAdminOtp });
  const submit = useMutation({ mutationFn: applyAdmin });

  const detectedDomain = form.applicantEmail.includes("@") ? form.applicantEmail.split("@")[1] : "";

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!form.idCardPhotoUrl) {
      toast.error("Please upload a photo of your campus ID card.");
      return;
    }
    try {
      await sendOtp.mutateAsync({ email: form.applicantEmail, fullName: form.fullName });
      toast.success(`OTP sent to ${form.applicantEmail}`);
      setStep("otp");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const handleVerifyAndSubmit = async (e) => {
    e.preventDefault();
    try {
      await verifyOtp.mutateAsync({ email: form.applicantEmail, otp });
      await submit.mutateAsync(form);
      setStep("done");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  const handleResend = async () => {
    try {
      await sendOtp.mutateAsync({ email: form.applicantEmail, fullName: form.fullName });
      toast.success("A new OTP has been sent.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };

  return (
    <main className="grid min-h-dvh place-items-center bg-background p-5">
      <form
        className="w-full max-w-lg space-y-5 rounded-[28px] border border-border-glow bg-surface p-6"
        onSubmit={step === "details" ? handleSendOtp : handleVerifyAndSubmit}
      >
        <div>
          <p className="text-sm font-bold text-primary-container">SMART CAMPUS FOOD</p>
          <h1 className="mt-2 text-2xl font-bold">Campus Admin Application</h1>
          <p className="mt-1 text-sm text-muted-text">
            {step === "details" && "Tell us about you and the campus you want to onboard."}
            {step === "otp" && `Enter the 6-digit code sent to ${form.applicantEmail}.`}
            {step === "done" && "Your application is in review."}
          </p>
        </div>

        {step === "details" && (
          <>
            <TextInput label="Full name" required value={form.fullName} onChange={set("fullName")} />
            <TextInput label="Campus email" type="email" required value={form.applicantEmail} onChange={set("applicantEmail")} />
            {detectedDomain && (
              <p className="-mt-1 text-xs text-muted-text">
                Campus domain detected: <span className="font-semibold text-primary-container">@{detectedDomain}</span>
              </p>
            )}
            <TextInput label="Designation" placeholder="e.g. Dean of Student Affairs" required value={form.designation} onChange={set("designation")} />
            <FileInput
              label="Campus ID card photo"
              required
              hint="Take a clear photo of your official campus ID card. This is reviewed by the SuperAdmin."
              value={form.idCardPhotoUrl}
              onChange={(base64) => setForm((prev) => ({ ...prev, idCardPhotoUrl: base64 }))}
            />
            <TextInput label="Campus name" required value={form.campusName} onChange={set("campusName")} />
            <TextInput label="Campus location" placeholder="City, State" required value={form.campusLocation} onChange={set("campusLocation")} />
            <Button className="w-full" loading={sendOtp.isPending} type="submit">
              Send verification code
            </Button>
          </>
        )}

        {step === "otp" && (
          <>
            <div className="flex items-center gap-3 rounded-2xl border border-border-glow bg-card-input p-4">
              <ShieldCheck className="text-primary-container" size={22} />
              <p className="text-sm text-muted-text">
                We sent a 6-digit code to <span className="font-semibold text-on-surface">{form.applicantEmail}</span>. It expires in 10 minutes.
              </p>
            </div>
            <OtpInput
              label="Enter OTP"
              required
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
            />
            <Button className="w-full" loading={verifyOtp.isPending || submit.isPending} type="submit">
              Verify &amp; submit application
            </Button>
            <button type="button" className="w-full text-sm text-primary" onClick={handleResend} disabled={sendOtp.isPending}>
              Resend code
            </button>
            <button type="button" className="w-full text-sm text-muted-text" onClick={() => setStep("details")}>
              ← Edit details
            </button>
          </>
        )}

        {step === "done" && (
          <div className="space-y-4 text-center">
            <CheckCircle2 className="mx-auto text-success" size={48} />
            <p className="text-sm text-muted-text">
              Your application for <span className="font-semibold text-on-surface">{form.campusName}</span> has been submitted.
              The SuperAdmin will review your ID card and details, then approve or reject your application.
            </p>
            <Link to={ROUTES.LOGIN} className="inline-block font-semibold text-primary">
              Back to login
            </Link>
          </div>
        )}
      </form>
    </main>
  );
}
