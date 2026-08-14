import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

export function renderWithProviders(ui: ReactElement, initialEntries: string[] = ["/"]) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

type Handler = {
  method: string;
  match: RegExp;
  respond: (url: string) => { status: number; body: unknown };
};

/**
 * A tiny fetch mock keyed by method + URL pattern. No mocking library, this
 * app only talks to one API, a handful of route matchers is enough. Fixture
 * response bodies are real captured API output (see src/test/fixtures),
 * never invented data.
 */
export function mockFetch(handlers: Handler[]) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const method = init?.method ?? "GET";
    const handler = handlers.find((h) => h.method === method && h.match.test(url));
    if (!handler) {
      throw new Error(`Unhandled fetch: ${method} ${url}`);
    }
    const { status, body } = handler.respond(url);
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}
