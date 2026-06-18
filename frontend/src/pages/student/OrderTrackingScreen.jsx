import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import client from "../../api/client";
import { API } from "../../constants/api-endpoints";
import EmptyState from "../../components/ui/EmptyState";

export default function OrderTrackingScreen() {
  const { id } = useParams();
  const query = useQuery({ queryKey: ["order", id], queryFn: async () => (await client.get(API.ORDER(id))).data, refetchInterval: 10000 });
  if (query.isLoading) return <EmptyState loading title="Tracking order" />;
  return <main className="min-h-dvh bg-background p-5"><h1 className="text-3xl font-bold">Order #{id}</h1><div className="mt-8 rounded-3xl border border-border-glow bg-card-input p-6"><p className="text-sm text-muted-text">Current status</p><p className="mt-2 text-3xl font-extrabold text-primary-container">{query.data?.status}</p><p className="mt-5 text-secondary">Pickup OTP: <strong className="text-on-surface">{query.data?.pickupOtp || "Available after payment"}</strong></p></div></main>;
}
