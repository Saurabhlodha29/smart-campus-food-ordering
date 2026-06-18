import Button from "../../components/ui/Button";
import { useAuthStore } from "../../store/authStore";
import { useAuth } from "../../hooks/useAuth";

export default function ProfileScreen() {
  const auth = useAuthStore(); const { logout } = useAuth();
  return <main className="min-h-dvh bg-background p-5"><h1 className="text-3xl font-bold">Profile</h1><div className="mt-6 rounded-3xl border border-border-glow bg-card-input p-6"><div className="grid h-20 w-20 place-items-center rounded-full bg-primary-container text-3xl font-bold">{auth.userName?.[0] || "U"}</div><h2 className="mt-4 text-2xl font-bold">{auth.userName}</h2><p className="text-muted-text">{auth.userEmail}</p><p className="mt-2 text-sm text-secondary">{auth.campusName}</p><Button className="mt-8 w-full" variant="outline" onClick={logout}>Sign out</Button></div></main>;
}
