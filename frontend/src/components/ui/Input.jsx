import clsx from "clsx";

export function TextInput({ label, error, className, ...props }) {
  return (
    <label className="block space-y-2">
      {label && <span className="text-xs font-semibold uppercase tracking-wider text-muted-text">{label}</span>}
      <input
        className={clsx(
          "h-[52px] w-full rounded-xl border border-border-glow bg-card-input px-4 text-on-surface outline-none placeholder:text-muted-text focus:border-primary-container",
          className,
        )}
        {...props}
      />
      {error && <span className="text-xs text-error">{error}</span>}
    </label>
  );
}

export function SearchBar(props) {
  return <TextInput type="search" placeholder="Search..." {...props} />;
}

export function OtpInput(props) {
  return <TextInput inputMode="numeric" maxLength={6} pattern="[0-9]{6}" {...props} />;
}
