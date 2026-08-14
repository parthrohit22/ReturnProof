import { useRef } from "react";
import { Upload } from "lucide-react";

interface JsonInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function JsonInput({ value, onChange }: JsonInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    onChange(text);
    event.target.value = "";
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label htmlFor="json-input" className="text-sm font-medium text-text-primary">
          Return shipment JSON
        </label>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-1.5 rounded border border-border-strong bg-surface px-2.5 py-1 text-xs font-medium text-text-primary hover:bg-surface-sunken"
        >
          <Upload size={13} aria-hidden="true" />
          Upload .json
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="application/json,.json"
          onChange={handleFileSelected}
          className="hidden"
          aria-hidden="true"
        />
      </div>
      <textarea
        id="json-input"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        spellCheck={false}
        placeholder='{"return_id": "RET-2026-001", "warehouse_report": { "items": [...] }, "supplier_events": [...] }'
        className="h-64 w-full resize-y rounded-md border border-border bg-surface-sunken p-3 font-mono text-xs leading-relaxed text-text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent"
      />
    </div>
  );
}
