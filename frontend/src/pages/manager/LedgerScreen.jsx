import { useQuery } from "@tanstack/react-query";
import { ledger, ledgerSummary, payouts } from "../../api/payouts";
import ManagerBottomNav from "../../components/layout/ManagerBottomNav";
import { DarkCard } from "../../components/ui/Card";
import { formatCurrency } from "../../utils/formatCurrency";

export default function LedgerScreen() {
  const entries=useQuery({queryKey:["ledger"],queryFn:()=>ledger()}); const summary=useQuery({queryKey:["ledger-summary"],queryFn:()=>ledgerSummary()}); const payoutQuery=useQuery({queryKey:["payouts"],queryFn:payouts});
  return <main className="manager-screen min-h-dvh bg-background p-5 pb-28"><h1 className="text-3xl font-bold">Earnings Ledger</h1><section className="mt-6 grid grid-cols-2 gap-4"><DarkCard className="p-4"><p className="text-xs text-muted-text">TODAY</p><p className="text-2xl font-bold text-primary-container">{formatCurrency(summary.data?.totalRevenue)}</p></DarkCard><DarkCard className="p-4"><p className="text-xs text-muted-text">ORDERS</p><p className="text-3xl font-bold">{summary.data?.totalOrders||0}</p></DarkCard></section><h2 className="mb-3 mt-7 text-xl font-bold">Transactions</h2><div className="space-y-3">{entries.data?.orders?.map((order)=><DarkCard className="flex justify-between p-4" key={order.orderId}><div><h3 className="font-bold">#{order.orderId}</h3><p className="text-sm text-muted-text">{order.customerName} · {order.paymentMode}</p></div><p className="font-bold">{formatCurrency(order.totalAmount)}</p></DarkCard>)}</div><h2 className="mb-3 mt-7 text-xl font-bold">Payouts</h2>{payoutQuery.data?.map((payout)=><DarkCard className="mb-3 flex justify-between p-4" key={payout.id}><span>{payout.status}</span><strong>{formatCurrency(payout.netAmount)}</strong></DarkCard>)}<ManagerBottomNav active="ledger"/></main>;
}
