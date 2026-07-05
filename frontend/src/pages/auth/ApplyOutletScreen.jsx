import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import FileInput from "../../components/ui/FileInput";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import { applyOutlet } from "../../api/applications";
import { ROUTES } from "../../constants/routes";

const emptyForm = {
  managerName: "",
  managerEmail: "",
  outletName: "",
  outletDescription: "",
  campusId: "",
  avgPrepTime: 15,
  licenseDocUrl: "",
  outletPhotoUrl: "",
  fssaiLicenseNumber: "",
  gstin: "",
  panNumber: "",
  bankAccountNumber: "",
  bankIfscCode: "",
};

export default function ApplyOutletScreen() {
  const [form, setForm] = useState(emptyForm);
  const [submitted, setSubmitted] = useState(false);

  const campuses = useQuery({
    queryKey: ["public-campuses"],
    queryFn: async () => (await client.get(API.CAMPUSES)).data,
  });

  const sortedCampuses = [...(campuses.data || [])]
    .filter((c) => c.status === "ACTIVE")
    .sort((a, b) => a.name.localeCompare(b.name));

  const mutation = useMutation({
    mutationFn: (data) =>
      applyOutlet({ ...data, campusId: Number(data.campusId), avgPrepTime: Number(data.avgPrepTime) }),
    onSuccess: () => setSubmitted(true),
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  if (submitted) {
    return (
      <main className="grid min-h-dvh place-items-center bg-background p-5">
        <div className="w-full max-w-lg space-y-4 rounded-[28px] border border-border-glow bg-surface p-8 text-center">
          <CheckCircle2 className="mx-auto text-success" size={48} />
          <h1 className="text-2xl font-bold">Application submitted!</h1>
          <p className="text-sm text-muted-text">
            Your documents are being automatically verified. The campus admin will review the result and either
            approve or reject your outlet — you will be notified once a decision is made.
          </p>
          <Link to={ROUTES.LOGIN} className="inline-block font-semibold text-primary">
            Back to login
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-background p-5">
      <form
        className="mx-auto max-w-lg space-y-5 rounded-[28px] border border-border-glow bg-surface p-6"
        onSubmit={(e) => {
          e.preventDefault();
          if (!form.campusId) return toast.error("Please select a campus.");
          if (!form.licenseDocUrl) return toast.error("Please upload your license/registration document photo.");
          mutation.mutate(form);
        }}
      >
        <div>
          <p className="text-sm font-bold text-primary-container">SMART CAMPUS FOOD</p>
          <h1 className="mt-2 text-2xl font-bold">Apply as Outlet Manager</h1>
          <p className="mt-1 text-sm text-muted-text">
            Any email works here — outlet staff don't need a campus email address.
          </p>
        </div>

        <TextInput label="Manager name" required value={form.managerName} onChange={set("managerName")} />
        <TextInput
          label="Manager email"
          type="email"
          required
          placeholder="any email, e.g. you@gmail.com"
          value={form.managerEmail}
          onChange={set("managerEmail")}
        />
        <TextInput label="Outlet name" required value={form.outletName} onChange={set("outletName")} />
        <TextInput label="Description" value={form.outletDescription} onChange={set("outletDescription")} />

        <label className="block space-y-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-text">Campus *</span>
          <select
            required
            value={form.campusId}
            onChange={set("campusId")}
            className="h-[52px] w-full rounded-xl border border-border-glow bg-card-input px-4 text-on-surface outline-none focus:border-primary-container"
          >
            <option value="" disabled>
              {campuses.isLoading ? "Loading campuses..." : "Select your campus"}
            </option>
            {sortedCampuses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.location}
              </option>
            ))}
          </select>
        </label>

        <TextInput
          label="Average preparation time (minutes)"
          type="number"
          min={1}
          required
          value={form.avgPrepTime}
          onChange={set("avgPrepTime")}
        />

        <FileInput
          label="License / registration document"
          required
          hint="A clear photo of your FSSAI certificate or trade license."
          value={form.licenseDocUrl}
          onChange={(base64) => setForm((prev) => ({ ...prev, licenseDocUrl: base64 }))}
        />
        <FileInput
          label="Outlet photo (optional)"
          hint="A photo of your stall/counter — shown to students once approved."
          value={form.outletPhotoUrl}
          onChange={(base64) => setForm((prev) => ({ ...prev, outletPhotoUrl: base64 }))}
        />

        <div className="grid grid-cols-2 gap-4">
          <TextInput label="FSSAI license no." value={form.fssaiLicenseNumber} onChange={set("fssaiLicenseNumber")} />
          <TextInput label="GSTIN" value={form.gstin} onChange={set("gstin")} />
          <TextInput label="PAN" value={form.panNumber} onChange={set("panNumber")} />
          <TextInput label="IFSC" value={form.bankIfscCode} onChange={set("bankIfscCode")} />
        </div>
        <TextInput label="Bank account number" value={form.bankAccountNumber} onChange={set("bankAccountNumber")} />

        <p className="text-xs text-muted-text">
          These are checked automatically against public government databases. A low score does NOT auto-reject you —
          the campus admin makes the final decision.
        </p>

        <Button className="w-full" loading={mutation.isPending} type="submit">
          Submit application
        </Button>
      </form>
    </main>
  );
}
