export const statusTone = (status = "") => {
  const value = status.toUpperCase();
  if (["ACTIVE", "READY", "PAID", "PICKED", "APPROVED"].includes(value)) return "success";
  if (["FAILED", "REJECTED", "CANCELLED", "SUSPENDED"].includes(value)) return "error";
  if (["PENDING", "PLACED", "PREPARING", "WARNING"].includes(value)) return "warning";
  return "neutral";
};
