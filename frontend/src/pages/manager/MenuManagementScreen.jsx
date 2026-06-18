import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getMyOutlet } from "../../api/outlets";
import { addItem, deleteItem, getAllMenu, setItemAvailability } from "../../api/menu";
import { apiErrorMessage } from "../../api/client";
import ManagerBottomNav from "../../components/layout/ManagerBottomNav";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import { DarkCard } from "../../components/ui/Card";
import { formatCurrency } from "../../utils/formatCurrency";

export default function MenuManagementScreen() {
  const [form, setForm] = useState({ name: "", price: "", prepTime: "", photoUrl: "" }); const queryClient = useQueryClient();
  const outlet = useQuery({ queryKey: ["my-outlet"], queryFn: getMyOutlet });
  const menu = useQuery({ queryKey: ["manager-menu", outlet.data?.id], queryFn: () => getAllMenu(outlet.data.id), enabled: Boolean(outlet.data?.id) });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["manager-menu"] });
  const create = useMutation({ mutationFn: () => addItem({ ...form, outletId: outlet.data.id, price: Number(form.price), prepTime: Number(form.prepTime) }), onSuccess: () => { toast.success("Menu item added"); setForm({ name: "", price: "", prepTime: "", photoUrl: "" }); refresh(); }, onError: (e) => toast.error(apiErrorMessage(e)) });
  const availability = useMutation({ mutationFn: setItemAvailability, onSuccess: refresh, onError: (e) => toast.error(apiErrorMessage(e)) });
  const remove = useMutation({ mutationFn: deleteItem, onSuccess: refresh, onError: (e) => toast.error(apiErrorMessage(e)) });
  return <main className="manager-screen min-h-dvh bg-background p-5 pb-28"><h1 className="text-3xl font-bold">Menu Management</h1><form className="mt-6 grid gap-3 rounded-3xl border border-border-glow bg-surface p-4" onSubmit={(e) => { e.preventDefault(); create.mutate(); }}><TextInput placeholder="Item name" required value={form.name} onChange={(e) => setForm({...form,name:e.target.value})}/><div className="grid grid-cols-2 gap-3"><TextInput placeholder="Price" type="number" required value={form.price} onChange={(e) => setForm({...form,price:e.target.value})}/><TextInput placeholder="Prep minutes" type="number" required value={form.prepTime} onChange={(e) => setForm({...form,prepTime:e.target.value})}/></div><TextInput placeholder="Photo URL (optional)" value={form.photoUrl} onChange={(e) => setForm({...form,photoUrl:e.target.value})}/><Button loading={create.isPending} type="submit">Add Item</Button></form><div className="mt-6 space-y-3">{menu.data?.map((item) => <DarkCard className="flex items-center gap-4 p-4" key={item.id}>{item.photoUrl && <img className="h-20 w-20 rounded-xl object-cover" src={item.photoUrl} alt="" />}<div className="flex-1"><h3 className="font-bold">{item.name}</h3><p className="text-primary">{formatCurrency(item.price)}</p><p className="text-xs text-muted-text">{item.prepTime} min</p></div><div className="grid gap-2"><Button variant="outline" onClick={() => availability.mutate({ id:item.id, available:!item.available })}>{item.available ? "Disable" : "Enable"}</Button><Button variant="danger" onClick={() => remove.mutate(item.id)}>Delete</Button></div></DarkCard>)}</div><ManagerBottomNav active="menu" /></main>;
}
