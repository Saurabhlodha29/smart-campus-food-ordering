import { Outlet } from "react-router-dom";
import BottomNav from "./BottomNav";

export default function StudentLayout() {
  return <div className="min-h-dvh bg-background pb-20"><Outlet /><BottomNav /></div>;
}
