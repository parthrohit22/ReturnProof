import type { ReturnAuditReport } from "./audit";

export type SummaryStatus = "RESOLVED" | "REQUIRES_REVIEW";

export interface RunSummary {
  id: string;
  return_id: string;
  scenario_name: string | null;
  summary_status: SummaryStatus;
  item_count: number;
  conflict_count: number;
  quantity_received: number;
  route_totals: Partial<Record<"RESTOCK" | "SCRAP" | "QUARANTINE", number>>;
  created_at: string;
}

export interface RunDetail extends RunSummary {
  input_payload: unknown;
  audit_report: ReturnAuditReport;
}

export interface ApiErrorDetail {
  path: string;
  message: string;
}

export interface ApiErrorBody {
  error: string;
  message: string;
  details: ApiErrorDetail[];
}

/** Thrown by the API client for any non-2xx response, carrying the
 * structured error body the backend returns whenever it can. */
export class ApiError extends Error {
  readonly status: number;
  readonly body: ApiErrorBody | null;

  constructor(status: number, body: ApiErrorBody | null) {
    super(body?.message ?? `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}
