import clsx from "clsx";

export function DarkCard({ className, ...props }) {
  return <div className={clsx("rounded-2xl border border-border-glow bg-card-input", className)} {...props} />;
}

export function GlassCard({ className, ...props }) {
  return <div className={clsx("glass rounded-2xl", className)} {...props} />;
}
