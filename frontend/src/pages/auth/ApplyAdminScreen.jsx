import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import { applyAdmin } from "../../api/applications";
import { apiErrorMessage } from "../../api/client";

export default function ApplyAdminScreen() {
  const [form, setForm] = useState({ fullName: "", applicantEmail: "", designation: "", idCardPhotoUrl: "", campusName: "", campusLocation: "", campusEmailDomain: "" });
  const mutation = useMutation({ mutationFn: applyAdmin, onSuccess: () => toast.success("Campus admin application submitted"), onError: (e) => toast.error(apiErrorMessage(e)) });
  return <ApplicationForm title="Campus Admin Application" form={form} setForm={setForm} mutation={mutation} fields={[["fullName","Full name"],["applicantEmail","Campus email","email"],["designation","Designation"],["idCardPhotoUrl","ID card photo URL","url"],["campusName","Campus name"],["campusLocation","Campus location"],["campusEmailDomain","Campus email domain"]]} />;
}

export function ApplicationForm({ title, form, setForm, mutation, fields }) {
  return <main className="min-h-dvh bg-background p-5"><form className="mx-auto max-w-lg space-y-5 rounded-[28px] border border-border-glow bg-surface p-6" onSubmit={(e) => { e.preventDefault(); mutation.mutate(form); }}><div><p className="text-sm font-bold text-primary-container">SMART CAMPUS FOOD</p><h1 className="mt-2 text-2xl font-bold">{title}</h1></div>{fields.map(([name,label,type="text"]) => <TextInput key={name} label={label} type={type} required value={form[name]} onChange={(e) => setForm({ ...form, [name]: e.target.value })} />)}<Button className="w-full" loading={mutation.isPending} type="submit">Submit application</Button></form></main>;
}
