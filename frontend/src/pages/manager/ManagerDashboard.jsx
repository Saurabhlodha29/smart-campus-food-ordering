import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getMyOutlet, toggleOutlet } from "../../api/outlets";
import { managerOrders, updateStatus } from "../../api/orders";
import { apiErrorMessage } from "../../api/client";
import ManagerBottomNav from "../../components/layout/ManagerBottomNav";
import Button from "../../components/ui/Button";
import { DarkCard } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/Badge";
import { formatCurrency } from "../../utils/formatCurrency";
import { statusTone } from "../../utils/statusHelpers";

export default function ManagerDashboard() {
  const queryClient = useQueryClient();
  const outlet = useQuery({ queryKey: ["my-outlet"], queryFn: getMyOutlet });
  const orders = useQuery({ queryKey: ["manager-orders", outlet.data?.id], queryFn: () => managerOrders(outlet.data.id), enabled: Boolean(outlet.data?.id), refetchInterval: 15000 });
  const toggle = useMutation({ mutationFn: () => toggleOutlet(outlet.data.id), onSuccess: () => { toast.success("Outlet status updated"); queryClient.invalidateQueries({ queryKey: ["my-outlet"] }); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  const advance = useMutation({ mutationFn: updateStatus, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["manager-orders"] }), onError: (e) => toast.error(apiErrorMessage(e)) });
  const live = orders.data?.filter((order) => ["PLACED","PREPARING","READY"].includes(order.status)) || [];
  return <main className="manager-screen min-h-dvh bg-background p-5 pb-28"><header className="flex items-center justify-between"><div><p className="text-sm text-muted-text">Managing</p><h1 className="text-2xl font-bold">{outlet.data?.name || "Your Outlet"}</h1></div><Button variant="outline" loading={toggle.isPending} onClick={() => toggle.mutate()}>{outlet.data?.status === "ACTIVE" ? "Close" : "Open"}</Button></header><section className="mt-6 grid grid-cols-2 gap-4"><DarkCard className="p-4"><p className="text-xs text-muted-text">LIVE ORDERS</p><p className="text-3xl font-extrabold">{live.length}</p></DarkCard><DarkCard className="p-4"><p className="text-xs text-muted-text">TODAY REVENUE</p><p className="text-2xl font-extrabold text-primary-container">{formatCurrency(orders.data?.filter((o) => o.paymentStatus === "PAID").reduce((sum,o) => sum + Number(o.totalAmount || 0), 0))}</p></DarkCard></section><h2 className="mb-3 mt-7 text-xl font-bold">Active orders</h2><div className="space-y-3">{live.map((order) => <DarkCard className="p-4" key={order.id}><div className="flex justify-between"><div><h3 className="font-bold">#{order.id}</h3><p className="text-sm text-muted-text">{order.student?.fullName || order.customerName}</p></div><StatusChip tone={statusTone(order.status)}>{order.status}</StatusChip></div>{order.status !== "READY" && <Button className="mt-4 w-full" onClick={() => advance.mutate({ id: order.id, status: order.status === "PLACED" ? "PREPARING" : "READY" })}>{order.status === "PLACED" ? "Start preparing" : "Mark ready"}</Button>}</DarkCard>)}</div><ManagerBottomNav active="dashboard" /></main>;
}
