import clsx from "clsx";

export function StatusChip({ children, tone = "neutral", className }) {
  const tones = {
    success: "bg-success/10 text-success",
    warning: "bg-accent-rating/10 text-accent-rating",
    error: "bg-error/10 text-error",
    neutral: "bg-surface-container-high text-on-surface-variant",
  };
  return <span className={clsx("rounded-full px-2.5 py-1 text-[11px] font-bold uppercase", tones[tone], className)}>{children}</span>;
}

export const CategoryChip = StatusChip;
