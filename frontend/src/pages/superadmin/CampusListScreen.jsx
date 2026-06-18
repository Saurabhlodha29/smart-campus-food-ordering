import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import client from "../../api/client";
import { API } from "../../constants/api-endpoints";
import ResourceListScreen from "../../components/screens/ResourceListScreen";
import { ROUTES } from "../../constants/routes";

export default function CampusListScreen() {
  const query = useQuery({ queryKey: ["campuses"], queryFn: async () => (await client.get(API.CAMPUSES)).data });
  return <ResourceListScreen title="Campuses" query={query} renderItem={(campus) => <Link to={ROUTES.SA_CAMPUS_DETAIL.replace(":id", campus.id)}><h3 className="font-bold">{campus.name}</h3><p className="text-sm text-muted-text">{campus.location} · @{campus.emailDomain}</p></Link>} />;
}
