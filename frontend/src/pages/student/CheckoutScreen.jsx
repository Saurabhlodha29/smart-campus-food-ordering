import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import Button from "../../components/ui/Button";
import { useCartStore } from "../../store/cartStore";
import { useAuthStore } from "../../store/authStore";
import { getSlots } from "../../api/slots";
import { placeOrder } from "../../api/orders";
import { apiErrorMessage } from "../../api/client";
import { useRazorpay } from "../../hooks/useRazorpay";
import { ROUTES } from "../../constants/routes";

export default function CheckoutScreen() {
  const cart = useCartStore(); const userId = useAuthStore((s) => s.userId); const navigate = useNavigate(); const razorpay = useRazorpay();
  const slots = useQuery({ queryKey: ["slots", cart.outletId], queryFn: () => getSlots(cart.outletId), enabled: Boolean(cart.outletId) });
  const order = useMutation({ mutationFn: placeOrder, onError: (e) => toast.error(apiErrorMessage(e)), onSuccess: async (data) => { const id = data.id || data.orderId; if (cart.paymentMethod === "ONLINE" && !(await razorpay.pay(id))) return; cart.clearCart(); navigate(ROUTES.STUDENT_TRACKING.replace(":id", id)); } });
  const submit = () => order.mutate({ studentId: userId, outletId: cart.outletId, slotId: cart.selectedSlotId, paymentMode: cart.paymentMethod, items: cart.items.map(({ item, quantity }) => ({ menuItemId: item.id, quantity })) });
  return <main className="min-h-dvh bg-background p-5"><h1 className="text-3xl font-bold">Checkout</h1><h2 className="mb-3 mt-6 font-bold">Pickup slot</h2><div className="grid grid-cols-2 gap-3">{slots.data?.map((slot) => <button key={slot.id} onClick={() => cart.setSlot(slot.id)} className={`rounded-xl border p-3 ${cart.selectedSlotId === slot.id ? "border-primary-container bg-primary-container/10" : "border-border-glow bg-card-input"}`}>{slot.startTime}–{slot.endTime}</button>)}</div><h2 className="mb-3 mt-6 font-bold">Payment</h2><div className="flex gap-3">{["ONLINE","CASH"].map((method) => <button key={method} className={`flex-1 rounded-xl border p-4 ${cart.paymentMethod === method ? "border-primary-container" : "border-border-glow"}`} onClick={() => cart.setPaymentMethod(method)}>{method}</button>)}</div><Button className="mt-8 w-full" loading={order.isPending || razorpay.loading} disabled={!cart.selectedSlotId} onClick={submit}>Place order</Button></main>;
}
