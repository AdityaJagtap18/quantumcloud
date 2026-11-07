export type JobStatus = "QUEUED" | "VALIDATING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface CircuitOperation {
  gate: string;
  qubits: number[];
  clbits?: number[];
  params?: number[];
  condition?: { clbit: number; equals: number };
}

export interface CircuitConfig {
  num_qubits: number;
  num_clbits: number;
  operations: CircuitOperation[];
}

export interface BackendInfo {
  id: string;
  name: string;
  backend_type: string;
  description: string;
  requires_measurements: boolean;
}

export interface Job {
  id: string;
  user_id: string;
  backend_id: string;
  circuit_config: CircuitConfig;
  shots: number;
  noise_config: Record<string, unknown> | null;
  status: JobStatus;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
  execution_time: number | null;
  error_message: string | null;
}

export interface JobResult {
  job_id: string;
  measurement_counts: Record<string, number> | null;
  probabilities: Record<string, number> | null;
  statevector: { real: number[]; imag: number[] } | null;
  execution_metadata: Record<string, unknown>;
}

export interface AlgorithmInfo {
  id: string;
  name: string;
  description: string;
  math_intuition: string;
  expected_distribution: Record<string, number> | null;
}

export interface DashboardStats {
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  running_jobs: number;
  queued_jobs: number;
  average_execution_time_seconds: number | null;
  recent_jobs: Array<{
    id: string;
    status: JobStatus;
    backend_id: string;
    submitted_at: string;
    execution_time: number | null;
  }>;
}

export interface ResourceReport {
  logical: {
    num_qubits: number;
    num_clbits: number;
    total_gate_count: number;
    single_qubit_gate_count: number;
    two_qubit_gate_count: number;
    depth: number;
    num_measurements: number;
    width: number;
    gate_distribution: Record<string, number>;
  };
  transpiled: {
    topology: string;
    transpiled_depth: number;
    transpiled_gate_count: number;
    native_gate_distribution: Record<string, number>;
    swap_gate_overhead: number;
    transpile_time_seconds: number;
    resource_overhead_ratio: number | null;
    depth_overhead_ratio: number | null;
  };
}

export interface ExperimentRun {
  id: string;
  noise_level: number;
  job_id: string | null;
  metrics: {
    measurement_counts: Record<string, number>;
    probabilities: Record<string, number>;
    observable_error: number;
    fidelity_proxy: number;
    execution_time_seconds: number;
  };
}

export interface Experiment {
  id: string;
  experiment_name: string;
  experiment_config: Record<string, unknown>;
  created_at: string;
}
