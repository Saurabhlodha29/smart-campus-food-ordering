import { Link } from "react-router-dom";
import { useCartStore } from "../../store/cartStore";
import { formatCurrency } from "../../utils/formatCurrency";
import QuantityPicker from "../../components/ui/QuantityPicker";
import Button from "../../components/ui/Button";
import { ROUTES } from "../../constants/routes";

export default function CartScreen() {
  const cart = useCartStore();
  return <main className="min-h-dvh bg-background p-5 pb-28"><h1 className="mb-6 text-3xl font-bold">Your cart</h1><div className="space-y-3">{cart.items.map(({ item, quantity }) => <div className="flex items-center justify-between rounded-2xl bg-card-input p-4" key={item.id}><div><h3 className="font-bold">{item.name}</h3><p className="text-primary">{formatCurrency(item.price * quantity)}</p></div><QuantityPicker value={quantity} onDecrease={() => cart.removeItem(item.id)} onIncrease={() => cart.addItem(item, cart.outletId)} /></div>)}</div><div className="mt-6 flex justify-between text-xl font-bold"><span>Total</span><span>{formatCurrency(cart.total())}</span></div><Link to={ROUTES.STUDENT_CHECKOUT}><Button className="mt-6 w-full" disabled={!cart.items.length}>Continue to checkout</Button></Link></main>;
}
