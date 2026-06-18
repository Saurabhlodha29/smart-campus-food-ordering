import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getOutletById } from "../../api/outlets";
import { getMenu } from "../../api/menu";
import { useCartStore } from "../../store/cartStore";
import { formatCurrency } from "../../utils/formatCurrency";
import QuantityPicker from "../../components/ui/QuantityPicker";
import { ROUTES } from "../../constants/routes";

export default function OutletDetailScreen() {
  const { id } = useParams();
  const outlet = useQuery({ queryKey: ["outlet", id], queryFn: () => getOutletById(id) });
  const menu = useQuery({ queryKey: ["menu", id], queryFn: () => getMenu(id) });
  const cart = useCartStore();
  return <main className="min-h-dvh bg-background pb-28"><div className="h-56 bg-card-input">{outlet.data?.photoUrl && <img className="h-full w-full object-cover" src={outlet.data.photoUrl} alt="" />}</div><section className="px-5 py-5"><h1 className="text-3xl font-bold">{outlet.data?.name || "Outlet"}</h1><p className="text-sm text-muted-text">{outlet.data?.avgPrepTime || 15} min average preparation</p><div className="mt-6 space-y-4">{menu.data?.map((item) => { const selected = cart.items.find((entry) => entry.item.id === item.id); return <div className="flex gap-4 rounded-2xl border border-border-glow bg-card-input p-4" key={item.id}><div className="flex-1"><h3 className="font-bold">{item.name}</h3><p className="text-primary">{formatCurrency(item.price)}</p><p className="text-xs text-muted-text">{item.prepTime} min</p></div>{selected ? <QuantityPicker value={selected.quantity} onDecrease={() => cart.removeItem(item.id)} onIncrease={() => cart.addItem(item, Number(id))} /> : <button className="rounded-full border border-primary-container px-4 text-primary-container" onClick={() => cart.addItem(item, Number(id))}>Add</button>}</div>; })}</div></section>{cart.itemCount() > 0 && <Link className="fixed bottom-24 left-1/2 z-40 flex w-[calc(100%-40px)] max-w-[390px] -translate-x-1/2 justify-between rounded-full bg-primary-container px-6 py-4 font-bold text-white" to={ROUTES.STUDENT_CART}><span>{cart.itemCount()} items</span><span>{formatCurrency(cart.total())} · View cart</span></Link>}</main>;
}
