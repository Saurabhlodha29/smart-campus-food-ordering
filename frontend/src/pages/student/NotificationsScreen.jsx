import { useQuery } from "@tanstack/react-query";
import { getNotifs } from "../../api/notifications";
import ResourceListScreen from "../../components/screens/ResourceListScreen";
import { timeAgo } from "../../utils/formatDate";

export default function NotificationsScreen() {
  const query = useQuery({ queryKey: ["notifications"], queryFn: getNotifs });
  return <ResourceListScreen title="Notifications" query={query} renderItem={(item) => <><h3 className="font-bold">{item.title || item.type}</h3><p className="text-sm text-secondary">{item.message}</p><p className="mt-2 text-xs text-muted-text">{timeAgo(item.createdAt)}</p></>} />;
}
