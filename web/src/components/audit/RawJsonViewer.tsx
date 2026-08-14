import { useState } from "react";
import { Check, ChevronDown, ChevronRight, Copy } from "lucide-react";

interface RawJsonViewerProps {
  title: string;
  data: unknown;
  defaultOpen?: boolean;
}

export function RawJsonViewer({ title, data, defaultOpen = false }: RawJsonViewerProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(data, null, 2);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="rounded-md border border-border bg-surface">
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex items-center gap-1.5 text-sm font-medium text-text-primary"
        >
          {open ? (
            <ChevronDown size={14} aria-hidden="true" />
          ) : (
            <ChevronRight size={14} aria-hidden="true" />
          )}
          {title}
        </button>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded border border-border-strong px-2 py-1 text-xs font-medium text-text-secondary hover:bg-surface-sunken"
        >
          {copied ? <Check size={12} aria-hidden="true" /> : <Copy size={12} aria-hidden="true" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      {open && (
        <pre className="max-h-[480px] overflow-auto border-t border-border bg-surface-sunken p-3 font-mono text-xs leading-relaxed text-text-primary">
          {text}
        </pre>
      )}
    </div>
  );
}
