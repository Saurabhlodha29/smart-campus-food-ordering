export default function Spinner({ className = "" }) {
  return <span className={`inline-block h-7 w-7 animate-spin rounded-full border-2 border-primary-container border-t-transparent ${className}`} />;
}
