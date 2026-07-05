import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { ChevronDown, ChevronUp, CheckCircle2, XCircle, ShieldQuestion, ShieldCheck, ShieldAlert } from "lucide-react";
import client, { apiErrorMessage } from "../../api/client";
import { API } from "../../constants/api-endpoints";
import { getAllOutletApplications, reviewOutletApplication } from "../../api/applications";
import Button from "../../components/ui/Button";
import { DarkCard } from "../../components/ui/Card";
import { StatusChip } from "../../components/ui/Badge";
import { TextInput } from "../../components/ui/Input";
import EmptyState from "../../components/ui/EmptyState";
import { statusTone } from "../../utils/statusHelpers";

const TABS = ["PENDING", "APPROVED", "REJECTED"];

export default function OutletAppsScreen() {
  const [tab, setTab] = useState("PENDING");
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ["outlet-applications-all"], queryFn: getAllOutletApplications });

  const review = useMutation({
    mutationFn: reviewOutletApplication,
    onSuccess: (data) => {
      toast.success(data.message || "Application reviewed");
      queryClient.invalidateQueries({ queryKey: ["outlet-applications-all"] });
      queryClient.invalidateQueries({ queryKey: ["outlet-applications"] });
      queryClient.invalidateQueries({ queryKey: ["campus-outlets"] });
    },
    onError: (e) => toast.error(apiErrorMessage(e)),
  });

  const items = (query.data || []).filter((a) => a.status === tab);

  return (
    <main className="min-h-dvh bg-background p-5 pb-28">
      <h1 className="text-3xl font-bold">Outlet Applications</h1>
      <p className="mt-1 text-sm text-muted-text">
        Documents are checked automatically against public databases. A failed automatic check does NOT reject the
        application for you — you always make the final call below.
      </p>

      <div className="mt-5 flex gap-2 rounded-2xl border border-border-glow bg-card-input p-1.5">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`flex-1 rounded-xl py-2 text-sm font-semibold transition ${
              tab === t ? "bg-primary-container text-white shadow-orange" : "text-muted-text"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="mt-5 space-y-4">
        {query.isLoading && <EmptyState loading title="Loading applications" />}
        {query.isError && <EmptyState title="Could not load applications" message={query.error?.message} />}
        {!query.isLoading && items.length === 0 && <EmptyState title={`No ${tab.toLowerCase()} applications`} />}
        {items.map((item) => (
          <ApplicationCard key={item.id} item={item} onReview={review.mutate} reviewing={review.isPending} />
        ))}
      </div>
    </main>
  );
}

function ApplicationCard({ item, onReview, reviewing }) {
  const [expanded, setExpanded] = useState(false);
  const [tempPassword, setTempPassword] = useState("Welcome@123");

  const report = useQuery({
    queryKey: ["verification-report", item.id],
    queryFn: async () => (await client.get(API.OUTLET_APPLICATION_VERIFICATION_REPORT(item.id))).data,
    enabled: expanded,
    retry: false,
  });

  const ReportIcon = !report.data
    ? ShieldQuestion
    : report.data.overallStatus === "PASSED"
    ? ShieldCheck
    : report.data.overallStatus === "FAILED"
    ? ShieldAlert
    : ShieldQuestion;

  return (
    <DarkCard className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold">{item.outletName}</h3>
          <p className="text-sm text-secondary">{item.managerName} · {item.managerEmail}</p>
          <p className="mt-1 text-xs text-muted-text">Attempt {item.attemptNumber} of 3</p>
        </div>
        <StatusChip tone={statusTone(item.status)}>{item.status}</StatusChip>
      </div>

      {item.outletDescription && <p className="mt-3 text-sm text-muted-text">{item.outletDescription}</p>}

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="mt-4 flex items-center gap-2 text-sm font-semibold text-primary-container"
      >
        <ReportIcon size={16} />
        Verification report
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded && (
        <div className="mt-3 space-y-2 rounded-xl border border-border-glow bg-surface p-4 text-sm">
          {report.isLoading && <p className="text-muted-text">Loading report...</p>}
          {report.isError && <p className="text-muted-text">Report not ready yet — verification may still be running.</p>}
          {report.data && (
            <>
              <div className="flex items-center justify-between">
                <span className="font-semibold">Overall score</span>
                <StatusChip tone={statusTone(report.data.overallStatus)}>
                  {report.data.overallScore}/100 · {report.data.overallStatus}
                </StatusChip>
              </div>
              <ReportRow label="FSSAI" ok={report.data.fssaiVerified} note={report.data.fssaiNote} />
              <ReportRow label="GSTIN" ok={report.data.gstVerified} note={report.data.gstNote} />
              <ReportRow label="PAN format" ok={report.data.panFormatValid} note={report.data.panNote} />
              <ReportRow label="Bank IFSC" ok={report.data.bankIfscValid} note={report.data.bankNote} />
            </>
          )}
        </div>
      )}

      {item.status === "PENDING" && (
        <div className="mt-4 space-y-3 border-t border-border-glow pt-4">
          <TextInput
            label="Temporary password for manager"
            value={tempPassword}
            onChange={(e) => setTempPassword(e.target.value)}
          />
          <div className="flex gap-3">
            <Button
              className="flex-1"
              loading={reviewing}
              onClick={() => onReview({ id: item.id, approved: true, temporaryPassword: tempPassword, message: "Approved" })}
            >
              <CheckCircle2 size={16} className="mr-1" /> Approve
            </Button>
            <Button
              variant="danger"
              className="flex-1"
              loading={reviewing}
              onClick={() => onReview({ id: item.id, approved: false, message: "Application rejected" })}
            >
              <XCircle size={16} className="mr-1" /> Reject
            </Button>
          </div>
        </div>
      )}
    </DarkCard>
  );
}

function ReportRow({ label, ok, note }) {
  const tone = ok === true ? "text-success" : ok === false ? "text-error" : "text-muted-text";
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="font-medium text-on-surface">{label}</span>
      <span className={`text-right text-xs ${tone}`}>{note || "Not checked"}</span>
    </div>
  );
}
