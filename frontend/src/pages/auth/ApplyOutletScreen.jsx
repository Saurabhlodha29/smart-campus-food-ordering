import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { applyOutlet } from "../../api/applications";
import { apiErrorMessage } from "../../api/client";
import { ApplicationForm } from "./ApplyAdminScreen";

export default function ApplyOutletScreen() {
  const [form, setForm] = useState({ managerName: "", managerEmail: "", outletName: "", outletDescription: "", campusId: "", avgPrepTime: 15, licenseDocUrl: "", outletPhotoUrl: "", fssaiLicenseNumber: "", gstin: "", panNumber: "", bankAccountNumber: "", bankIfscCode: "" });
  const mutation = useMutation({ mutationFn: (data) => applyOutlet({ ...data, campusId: Number(data.campusId), avgPrepTime: Number(data.avgPrepTime) }), onSuccess: () => toast.success("Outlet application submitted"), onError: (e) => toast.error(apiErrorMessage(e)) });
  return <ApplicationForm title="Apply as Outlet Manager" form={form} setForm={setForm} mutation={mutation} fields={[["managerName","Manager name"],["managerEmail","Manager email","email"],["outletName","Outlet name"],["outletDescription","Description"],["campusId","Campus ID","number"],["avgPrepTime","Average preparation time","number"],["licenseDocUrl","License document URL","url"],["outletPhotoUrl","Outlet photo URL","url"],["fssaiLicenseNumber","FSSAI license"],["gstin","GSTIN"],["panNumber","PAN"],["bankAccountNumber","Bank account"],["bankIfscCode","IFSC"]]} />;
}
