import { Loader2 } from "lucide-react";

interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Loading…" }: LoadingStateProps) {
  return (
    <div
      role="status"
      className="flex flex-col items-center justify-center gap-2 px-6 py-10 text-text-secondary"
    >
      <Loader2 size={22} className="animate-spin" aria-hidden="true" />
      <p className="text-sm">{label}</p>
    </div>
  );
}
