import { useQuery } from "@tanstack/react-query";
import client from "../../api/client";
import { API } from "../../constants/api-endpoints";
import ManagerBottomNav from "../../components/layout/ManagerBottomNav";
import { DarkCard } from "../../components/ui/Card";
import { formatCurrency } from "../../utils/formatCurrency";

export default function AnalyticsScreen() {
  const query=useQuery({queryKey:["weekly-analytics"],queryFn:async()=>(await client.get(API.WEEKLY_ANALYTICS)).data});
  const total=query.data?.reduce((sum,day)=>sum+Number(day.revenue||0),0)||0; const max=Math.max(...(query.data?.map((d)=>Number(d.revenue||0))||[1]));
  return <main className="manager-screen min-h-dvh bg-background p-5 pb-28"><h1 className="text-3xl font-bold">Analytics</h1><section className="mt-6 grid grid-cols-2 gap-4"><DarkCard className="p-5"><p className="text-xs text-muted-text">7-DAY REVENUE</p><p className="mt-2 text-2xl font-bold text-primary-container">{formatCurrency(total)}</p></DarkCard><DarkCard className="p-5"><p className="text-xs text-muted-text">ORDERS</p><p className="mt-2 text-3xl font-bold">{query.data?.reduce((s,d)=>s+Number(d.orderCount||0),0)||0}</p></DarkCard></section><DarkCard className="mt-6 p-5"><h2 className="font-bold">Revenue over time</h2><div className="mt-6 flex h-52 items-end gap-3">{query.data?.map((day)=><div className="flex flex-1 flex-col items-center gap-2" key={day.date}><div className="w-full rounded-t bg-primary-container" style={{height:`${Math.max(8,Number(day.revenue||0)/max*100)}%`}}/><span className="text-[10px] text-muted-text">{day.date?.slice(5)}</span></div>)}</div></DarkCard><ManagerBottomNav active="dashboard"/></main>;
}
