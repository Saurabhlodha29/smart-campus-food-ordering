import { useRef, useState } from "react";
import { ImagePlus, X, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { compressImageToBase64 } from "../../utils/imageToBase64";

export default function FileInput({ label, hint, value, onChange, required }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const base64 = await compressImageToBase64(file);
      onChange(base64);
    } catch (err) {
      toast.error(err.message || "Could not process image");
    } finally {
      setBusy(false);
    }
  };

  return (
    <label className="block space-y-2">
      {label && (
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-text">
          {label}
          {required && <span className="text-error"> *</span>}
        </span>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
      {value ? (
        <div className="relative overflow-hidden rounded-xl border border-border-glow bg-card-input">
          <img src={value} alt="Uploaded preview" className="h-40 w-full object-cover" />
          <button
            type="button"
            onClick={() => onChange("")}
            className="absolute right-2 top-2 grid h-8 w-8 place-items-center rounded-full bg-black/60 text-white"
          >
            <X size={16} />
          </button>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="absolute bottom-2 right-2 rounded-full bg-black/60 px-3 py-1 text-xs font-semibold text-white"
          >
            Replace
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="flex h-40 w-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border-glow bg-card-input text-muted-text transition hover:border-primary-container disabled:opacity-60"
        >
          {busy ? <Loader2 className="animate-spin" size={28} /> : <ImagePlus size={28} />}
          <span className="text-sm font-medium">{busy ? "Processing..." : "Tap to upload a photo"}</span>
        </button>
      )}
      {hint && <span className="block text-xs text-muted-text">{hint}</span>}
    </label>
  );
}
