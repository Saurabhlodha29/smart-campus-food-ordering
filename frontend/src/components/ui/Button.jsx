import clsx from "clsx";

const variants = {
  primary: "bg-primary-container text-white shadow-orange",
  secondary: "bg-surface-container-high text-on-surface",
  outline: "border border-primary-container text-primary-container",
  danger: "border border-error/50 text-error",
};

export default function Button({ children, className, variant = "primary", loading, disabled, ...props }) {
  return (
    <button
      className={clsx(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-full px-5 font-semibold transition active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent" /> : children}
    </button>
  );
}
