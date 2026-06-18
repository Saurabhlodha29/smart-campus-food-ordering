import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { getMyOutlet } from "../../api/outlets";
import { createSlot, deleteSlot, getSlots } from "../../api/slots";
import { apiErrorMessage } from "../../api/client";
import ManagerBottomNav from "../../components/layout/ManagerBottomNav";
import Button from "../../components/ui/Button";
import { TextInput } from "../../components/ui/Input";
import { DarkCard } from "../../components/ui/Card";

export default function SlotManagementScreen() {
  const [form,setForm]=useState({startTime:"",endTime:"",maxOrders:20}); const queryClient=useQueryClient();
  const outlet=useQuery({queryKey:["my-outlet"],queryFn:getMyOutlet});
  const slots=useQuery({queryKey:["slots",outlet.data?.id],queryFn:()=>getSlots(outlet.data.id),enabled:Boolean(outlet.data?.id)});
  const refresh=()=>queryClient.invalidateQueries({queryKey:["slots"]});
  const create=useMutation({mutationFn:()=>createSlot({...form,outletId:outlet.data.id,maxOrders:Number(form.maxOrders)}),onSuccess:()=>{toast.success("Pickup slot created");refresh();},onError:(e)=>toast.error(apiErrorMessage(e))});
  const remove=useMutation({mutationFn:deleteSlot,onSuccess:refresh,onError:(e)=>toast.error(apiErrorMessage(e))});
  return <main className="manager-screen min-h-dvh bg-background p-5 pb-28"><h1 className="text-3xl font-bold">Pickup Slots</h1><form className="mt-6 grid grid-cols-2 gap-3 rounded-3xl border border-border-glow bg-surface p-4" onSubmit={(e)=>{e.preventDefault();create.mutate();}}><TextInput label="Starts" type="time" required value={form.startTime} onChange={(e)=>setForm({...form,startTime:e.target.value})}/><TextInput label="Ends" type="time" required value={form.endTime} onChange={(e)=>setForm({...form,endTime:e.target.value})}/><TextInput className="col-span-2" label="Capacity" type="number" required value={form.maxOrders} onChange={(e)=>setForm({...form,maxOrders:e.target.value})}/><Button className="col-span-2" loading={create.isPending} type="submit">Create slot</Button></form><div className="mt-6 space-y-3">{slots.data?.map((slot)=><DarkCard className="flex items-center justify-between p-4" key={slot.id}><div><h3 className="font-bold">{slot.startTime}–{slot.endTime}</h3><p className="text-sm text-muted-text">{slot.currentOrders}/{slot.maxOrders} orders</p></div><Button variant="danger" disabled={slot.currentOrders>0} onClick={()=>remove.mutate(slot.id)}>Delete</Button></DarkCard>)}</div><ManagerBottomNav active="slots"/></main>;
}
