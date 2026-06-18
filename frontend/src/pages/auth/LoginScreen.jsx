import { useState } from "react";
import { Link } from "react-router-dom";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import { useAuth } from "../../hooks/useAuth";
import { ROUTES } from "../../constants/routes";

export default function LoginScreen() {
  const [form, setForm] = useState({ email: "", password: "" });
  const { login } = useAuth();

  const submit = (event) => {
    event.preventDefault();
    login.mutate(form);
  };

  return (
    <main className="grid min-h-dvh place-items-center bg-background p-5">
      <form className="w-full max-w-sm space-y-6 rounded-[28px] border border-border-glow bg-surface p-6" onSubmit={submit}>
        <div><p className="text-sm font-semibold text-primary-container">SMART CAMPUS FOOD</p><h1 className="mt-2 text-3xl font-extrabold">Welcome back</h1><p className="mt-2 text-sm text-muted-text">Sign in to continue to your campus food dashboard.</p></div>
        <TextInput label="Email" type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <TextInput label="Password" type="password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <Button className="w-full" loading={login.isPending} type="submit">Sign In</Button>
        <div className="grid gap-2 text-center text-sm"><Link className="text-primary" to={ROUTES.REGISTER}>Create student account</Link><Link className="text-muted-text" to={ROUTES.APPLY_ADMIN}>Apply as campus admin</Link><Link className="text-muted-text" to={ROUTES.APPLY_OUTLET}>Apply as outlet manager</Link></div>
      </form>
    </main>
  );
}
