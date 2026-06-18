import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getOutlets } from "../../api/outlets";
import { useAuthStore } from "../../store/authStore";
import { ROUTES } from "../../constants/routes";
import EmptyState from "../../components/ui/EmptyState";
import { DarkCard } from "../../components/ui/Card";

export default function HomeScreen() {
  const campusId = useAuthStore((state) => state.campusId);
  const userName = useAuthStore((state) => state.userName);
  const query = useQuery({ queryKey: ["outlets", campusId], queryFn: () => getOutlets(campusId), enabled: Boolean(campusId) });
  return <main className="min-h-dvh bg-background px-5 pb-28 pt-6"><header className="mb-6"><p className="text-sm text-muted-text">Good day,</p><h1 className="text-3xl font-extrabold">{userName || "Student"} 👋</h1><p className="mt-2 text-sm text-secondary">What are you craving on campus?</p></header><div className="mb-6 flex h-[52px] items-center rounded-2xl bg-card-input px-4 text-muted-text"><span className="material-symbols-outlined mr-3">search</span>Search outlets and dishes</div>{query.isLoading ? <EmptyState loading title="Finding campus outlets" /> : query.data?.length ? <section className="space-y-4"><h2 className="text-xl font-bold">Campus outlets</h2>{query.data.map((outlet) => <Link key={outlet.id} to={ROUTES.STUDENT_OUTLET.replace(":id", outlet.id)}><DarkCard className="mb-4 overflow-hidden"><div className="h-36 bg-surface-container-high">{outlet.photoUrl && <img className="h-full w-full object-cover" src={outlet.photoUrl} alt="" />}</div><div className="p-4"><div className="flex justify-between"><h3 className="font-bold">{outlet.name}</h3><span className="text-accent-rating">★ {outlet.averageRating || "New"}</span></div><p className="mt-1 text-sm text-muted-text">{outlet.status} · {outlet.avgPrepTime || 15} min</p></div></DarkCard></Link>)}</section> : <EmptyState title="No outlets available" message="Your campus outlets will appear here when they open." />}</main>;
}
