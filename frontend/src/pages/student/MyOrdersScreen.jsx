import { useQuery } from "@tanstack/react-query";
import { myOrders } from "../../api/orders";
import { useAuthStore } from "../../store/authStore";
import ResourceListScreen from "../../components/screens/ResourceListScreen";
import { formatCurrency } from "../../utils/formatCurrency";
import { StatusChip } from "../../components/ui/Badge";
import { statusTone } from "../../utils/statusHelpers";

export default function MyOrdersScreen() {
  const userId = useAuthStore((s) => s.userId);
  const query = useQuery({ queryKey: ["orders", userId], queryFn: () => myOrders(userId), enabled: Boolean(userId) });
  return <ResourceListScreen title="My Orders" query={query} renderItem={(order) => <div className="flex justify-between"><div><h3 className="font-bold">Order #{order.id}</h3><p className="text-sm text-muted-text">{order.outlet?.name || order.outletName}</p><p className="text-primary">{formatCurrency(order.totalAmount)}</p></div><StatusChip tone={statusTone(order.status)}>{order.status}</StatusChip></div>} />;
}
