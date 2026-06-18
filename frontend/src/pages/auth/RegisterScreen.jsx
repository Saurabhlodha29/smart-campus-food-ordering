import { useState } from "react";
import Button from "../../components/ui/Button";
import { OtpInput, TextInput } from "../../components/ui/Input";
import { useAuth } from "../../hooks/useAuth";

export default function RegisterScreen() {
  const [step, setStep] = useState("register");
  const [form, setForm] = useState({ fullName: "", email: "", password: "", otp: "" });
  const { register, verify, resend } = useAuth();

  const submit = (event) => {
    event.preventDefault();
    if (step === "register") register.mutate(form, { onSuccess: () => setStep("verify") });
    else verify.mutate({ email: form.email, otp: form.otp });
  };

  return (
    <main className="grid min-h-dvh place-items-center bg-background p-5">
      <form className="w-full max-w-sm space-y-5 rounded-[28px] border border-border-glow bg-surface p-6" onSubmit={submit}>
        <h1 className="text-2xl font-bold">{step === "register" ? "Student registration" : "Verify your email"}</h1>
        {step === "register" ? <>
          <TextInput label="Full name" required value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
          <TextInput label="Campus email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <TextInput label="Password" type="password" minLength={6} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </> : <>
          <p className="text-sm text-muted-text">Enter the six-digit OTP sent to {form.email}.</p>
          <OtpInput label="OTP" required value={form.otp} onChange={(e) => setForm({ ...form, otp: e.target.value.replace(/\D/g, "") })} />
        </>}
        <Button className="w-full" loading={register.isPending || verify.isPending} type="submit">{step === "register" ? "Send verification code" : "Verify and continue"}</Button>
        {step === "verify" && <button className="w-full text-sm text-primary" type="button" onClick={() => resend.mutate(form.email)}>Resend OTP</button>}
      </form>
    </main>
  );
}
