import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { backendsApi, jobsApi } from "../api/endpoints";
import type { BackendInfo, Job, JobStatus } from "../types";
import { LoadingState, EmptyState, ErrorState } from "../components/States";
import { StatusBadge } from "../components/ui/StatusBadge";
import { PageHeader } from "../components/ui/PageHeader";
import { Select } from "../components/ui/Input";
import { Table, THead, Th, Td, Tr } from "../components/ui/Table";

const STATUS_OPTIONS: (JobStatus | "ALL")[] = ["ALL", "QUEUED", "VALIDATING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"];

export function JobExplorer() {
  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [backends, setBackends] = useState<BackendInfo[]>([]);
  const [statusFilter, setStatusFilter] = useState<JobStatus | "ALL">("ALL");
  const [backendFilter, setBackendFilter] = useState<string>("ALL");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    backendsApi.list().then((r) => setBackends(r.data));
  }, []);

  useEffect(() => {
    setJobs(null);
    jobsApi
      .list({
        status: statusFilter === "ALL" ? undefined : statusFilter,
        backend_id: backendFilter === "ALL" ? undefined : backendFilter,
      })
      .then((r) => setJobs(r.data))
      .catch(() => setError("Failed to load jobs."));
  }, [statusFilter, backendFilter]);

  function backendName(id: string) {
    return backends.find((b) => b.id === id)?.name ?? id.slice(0, 8);
  }

  return (
    <div>
      <PageHeader title="Jobs" description="Every quantum circuit execution you've submitted." />

      <div className="mb-4 flex gap-2">
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as JobStatus | "ALL")} className="w-40">
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>{s === "ALL" ? "All statuses" : s}</option>
          ))}
        </Select>
        <Select value={backendFilter} onChange={(e) => setBackendFilter(e.target.value)} className="w-48">
          <option value="ALL">All backends</option>
          {backends.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </Select>
      </div>

      {error && <ErrorState message={error} />}
      {!error && jobs === null && <LoadingState label="Loading jobs" />}
      {!error && jobs !== null && jobs.length === 0 && (
        <EmptyState title="No jobs match these filters" hint="Submit a circuit from Circuit Lab to see it here." />
      )}
      {!error && jobs !== null && jobs.length > 0 && (
        <Table>
          <THead>
            <Th>Job ID</Th>
            <Th>Backend</Th>
            <Th>Status</Th>
            <Th>Qubits</Th>
            <Th>Shots</Th>
            <Th>Submitted</Th>
            <Th>Duration</Th>
          </THead>
          <tbody>
            {jobs.map((job) => (
              <Tr key={job.id} onClick={() => navigate(`/jobs/${job.id}`)}>
                <Td mono>{job.id.slice(0, 8)}</Td>
                <Td mono>{backendName(job.backend_id)}</Td>
                <Td><StatusBadge status={job.status} /></Td>
                <Td mono>{job.circuit_config.num_qubits}</Td>
                <Td mono>{job.shots}</Td>
                <Td>{new Date(job.submitted_at).toLocaleString()}</Td>
                <Td mono>{job.execution_time !== null ? `${job.execution_time.toFixed(4)}s` : "—"}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
