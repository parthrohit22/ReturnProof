import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "./client";
import type { RunDetail, RunSummary } from "../../types/api";

const keys = {
  examples: ["examples"] as const,
  example: (name: string) => ["examples", name] as const,
  runs: ["reconciliations"] as const,
  run: (id: string) => ["reconciliations", id] as const,
};

export function useExamples() {
  return useQuery({
    queryKey: keys.examples,
    queryFn: () => apiClient.get<{ examples: string[] }>("/examples"),
    select: (data) => data.examples,
  });
}

export function useExample(name: string | null) {
  return useQuery({
    queryKey: keys.example(name ?? ""),
    queryFn: () => apiClient.get<Record<string, unknown>>(`/examples/${name}`),
    enabled: name !== null,
  });
}

export function useReconciliations() {
  return useQuery({
    queryKey: keys.runs,
    queryFn: () => apiClient.get<RunSummary[]>("/reconciliations"),
  });
}

export function useReconciliation(id: string | undefined) {
  return useQuery({
    queryKey: keys.run(id ?? ""),
    queryFn: () => apiClient.get<RunDetail>(`/reconciliations/${id}`),
    enabled: id !== undefined,
  });
}

interface CreateReconciliationInput {
  payload: unknown;
  scenarioName?: string | null;
}

export function useCreateReconciliation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ payload, scenarioName }: CreateReconciliationInput) => {
      const query = scenarioName ? `?scenario_name=${encodeURIComponent(scenarioName)}` : "";
      return apiClient.post<RunDetail>(`/reconciliations${query}`, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.runs });
    },
  });
}

export function useDeleteReconciliation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.delete(`/reconciliations/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.runs });
    },
  });
}
