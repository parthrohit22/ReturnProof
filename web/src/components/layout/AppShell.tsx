import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { ExternalLink, ListChecks, PlusCircle, ShieldCheck } from "lucide-react";

interface AppShellProps {
  children: ReactNode;
}

const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2 rounded px-3 py-1.5 text-sm font-medium transition-colors ${
    isActive
      ? "bg-accent-surface text-accent"
      : "text-text-secondary hover:bg-surface-sunken hover:text-text-primary"
  }`;

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center justify-between gap-6 px-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded bg-accent text-text-inverse">
                <ShieldCheck size={16} aria-hidden="true" />
              </span>
              <div className="leading-tight">
                <p className="text-sm font-semibold text-text-primary">ReturnProof</p>
                <p className="text-[11px] text-text-muted">
                  Evidence-driven return reconciliation
                </p>
              </div>
            </div>
            <nav className="flex items-center gap-1" aria-label="Primary">
              <NavLink to="/returns" className={navLinkClasses} end>
                <ListChecks size={15} aria-hidden="true" />
                Returns
              </NavLink>
              <NavLink to="/returns/new" className={navLinkClasses}>
                <PlusCircle size={15} aria-hidden="true" />
                New Reconciliation
              </NavLink>
            </nav>
          </div>
          <a
            href="/api/v1/docs"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-surface-sunken hover:text-text-primary"
          >
            API
            <ExternalLink size={13} aria-hidden="true" />
          </a>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
