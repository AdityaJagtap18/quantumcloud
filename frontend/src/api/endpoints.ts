import { apiClient } from "./client";
import type {
  AlgorithmInfo,
  BackendInfo,
  CircuitConfig,
  DashboardStats,
  Experiment,
  ExperimentRun,
  Job,
  JobResult,
  ResourceReport,
} from "../types";

export const authApi = {
  register: (email: string, password: string) => apiClient.post("/api/auth/register", { email, password }),
  login: (email: string, password: string) =>
    apiClient.post<{ access_token: string }>("/api/auth/login", { email, password }),
};

export const backendsApi = {
  list: () => apiClient.get<BackendInfo[]>("/api/backends"),
};

export const circuitsApi = {
  validate: (circuit: CircuitConfig) =>
    apiClient.post<{ valid: boolean; error: string | null }>("/api/circuits/validate", { circuit }),
  analyze: (circuit: CircuitConfig, topology: string) =>
    apiClient.post<ResourceReport>("/api/circuits/analyze", { circuit, topology }),
  transpile: (circuit: CircuitConfig, topology: string, optimization_level = 1) =>
    apiClient.post("/api/circuits/transpile", { circuit, topology, optimization_level }),
};

export const jobsApi = {
  submit: (circuit: CircuitConfig, backend_id: string, shots: number, noise_config?: Record<string, unknown>) =>
    apiClient.post<Job>("/api/jobs", { circuit, backend_id, shots, noise_config }),
  list: (params?: { status?: string; backend_id?: string }) => apiClient.get<Job[]>("/api/jobs", { params }),
  get: (jobId: string) => apiClient.get<Job>(`/api/jobs/${jobId}`),
  cancel: (jobId: string) => apiClient.post<Job>(`/api/jobs/${jobId}/cancel`),
  results: (jobId: string) => apiClient.get<JobResult>(`/api/jobs/${jobId}/results`),
};

export const experimentsApi = {
  create: (payload: {
    experiment_name: string;
    circuit: CircuitConfig;
    backend_id: string;
    shots: number;
    noise_levels: number[];
  }) => apiClient.post<Experiment>("/api/experiments", payload),
  list: () => apiClient.get<Experiment[]>("/api/experiments"),
  get: (experimentId: string) =>
    apiClient.get<{ experiment: Experiment; runs: ExperimentRun[] }>(`/api/experiments/${experimentId}`),
};

export const algorithmsApi = {
  list: () => apiClient.get<AlgorithmInfo[]>("/api/algorithms"),
  load: (algorithmId: string) => apiClient.post<{ circuit: CircuitConfig }>(`/api/algorithms/${algorithmId}/load`),
};

export const dashboardApi = {
  stats: () => apiClient.get<DashboardStats>("/api/dashboard/stats"),
};
