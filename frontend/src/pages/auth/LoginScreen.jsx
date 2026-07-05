import { useState } from "react";
import { Link } from "react-router-dom";
import { UtensilsCrossed } from "lucide-react";
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
    <main className="relative grid min-h-dvh place-items-center overflow-hidden bg-background p-5">
      <div className="pointer-events-none absolute -top-24 -left-20 h-72 w-72 rounded-full bg-primary-container/20 blur-3xl" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full bg-primary-container/10 blur-3xl" />

      <form
        className="relative w-full max-w-sm space-y-7 rounded-[32px] border border-border-glow bg-surface/90 p-8 shadow-glass backdrop-blur"
        onSubmit={submit}
      >
        <div className="flex flex-col items-center text-center">
          <div className="mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-primary-container shadow-orange">
            <UtensilsCrossed className="text-white" size={30} />
          </div>
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-container">Smart Campus Food</p>
          <h1 className="mt-3 text-4xl font-extrabold">Welcome back</h1>
          <p className="mt-2 text-sm text-muted-text">Sign in to continue to your campus food dashboard.</p>
        </div>

        <div className="space-y-5">
          <TextInput
            label="Email"
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <TextInput
            label="Password"
            type="password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </div>

        <Button className="w-full" loading={login.isPending} type="submit">
          Sign In
        </Button>

        <div className="grid gap-2.5 text-center text-sm">
          <Link className="font-semibold text-primary" to={ROUTES.REGISTER}>Create student account</Link>
          <Link className="text-muted-text" to={ROUTES.APPLY_ADMIN}>Apply as campus admin</Link>
          <Link className="text-muted-text" to={ROUTES.APPLY_OUTLET}>Apply as outlet manager</Link>
        </div>
      </form>
    </main>
  );
}
