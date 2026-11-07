import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Label as RLabel } from "recharts";
import { jobsApi } from "../api/endpoints";
import type { Job, JobResult } from "../types";
import { LoadingState, ErrorState } from "../components/States";
import { StatusBadge } from "../components/ui/StatusBadge";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";

const POLL_STATUSES = new Set(["QUEUED", "VALIDATING", "RUNNING"]);

export function JobDetails() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    if (!jobId) return;
    try {
      const jobResp = await jobsApi.get(jobId);
      setJob(jobResp.data);

      if (jobResp.data.status === "COMPLETED") {
        const resultResp = await jobsApi.results(jobId);
        setResult(resultResp.data);
      }

      if (POLL_STATUSES.has(jobResp.data.status)) {
        timerRef.current = setTimeout(refresh, 1500);
      }
    } catch {
      setError("Failed to load job.");
    }
  }, [jobId]);

  useEffect(() => {
    refresh();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [refresh]);

  async function handleCancel() {
    if (!jobId) return;
    try {
      const resp = await jobsApi.cancel(jobId);
      setJob(resp.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Could not cancel job");
    }
  }

  function exportJson() {
    if (!result) return;
    const blob = new Blob([JSON.stringify({ job, result }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `job-${jobId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportCsv() {
    if (!result?.measurement_counts) return;
    const rows = ["bitstring,count"].concat(
      Object.entries(result.measurement_counts).map(([k, v]) => `${k},${v}`)
    );
    const blob = new Blob([rows.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `job-${jobId}-counts.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (error) return <ErrorState message={error} />;
  if (!job) return <LoadingState label="Loading job" />;

  const totalShots = result?.measurement_counts
    ? Object.values(result.measurement_counts).reduce((a, b) => a + b, 0)
    : 0;

  const histogramData = result?.measurement_counts
    ? Object.entries(result.measurement_counts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([bitstring, count]) => ({ bitstring, count, probability: count / totalShots }))
    : [];

  const statevectorData =
    result?.statevector && result.probabilities
      ? Object.entries(result.probabilities).map(([bitstring, prob]) => ({ bitstring, probability: prob }))
      : [];

  return (
    <div>
      <PageHeader
        title={`Job ${job.id.slice(0, 8)}`}
        actions={
          <>
            <StatusBadge status={job.status} />
            {(job.status === "QUEUED" || job.status === "VALIDATING") && (
              <Button size="sm" onClick={handleCancel}>Cancel job</Button>
            )}
          </>
        }
      />

      {job.status === "FAILED" && job.error_message && (
        <div className="mb-6">
          <ErrorState message={job.error_message} />
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Meta label="Qubits" value={job.circuit_config.num_qubits} />
        <Meta label="Shots" value={job.shots} />
        <Meta label="Submitted" value={new Date(job.submitted_at).toLocaleString()} />
        <Meta label="Execution time" value={job.execution_time !== null ? `${job.execution_time.toFixed(4)}s` : "—"} />
      </div>

      {(job.status === "QUEUED" || job.status === "VALIDATING" || job.status === "RUNNING") && (
        <LoadingState label={`Job is ${job.status.toLowerCase()}`} />
      )}

      {histogramData.length > 0 && (
        <Card className="mb-4">
          <div className="mb-1 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-[var(--text)]">Measurement histogram</h2>
              <p className="text-xs text-[var(--text-secondary)]">
                Raw counts out of {job.shots} shots on {result?.execution_metadata.backend_name as string}
              </p>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={exportJson}>Export JSON</Button>
              <Button size="sm" onClick={exportCsv}>Export CSV</Button>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={histogramData} margin={{ left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="bitstring" tick={{ fontSize: 11, fill: "var(--text-secondary)" }}>
                <RLabel value="Measured bitstring" offset={-4} position="insideBottom" fill="var(--text-muted)" fontSize={10} />
              </XAxis>
              <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }}>
                <RLabel value="Count" angle={-90} position="insideLeft" fill="var(--text-muted)" fontSize={10} />
              </YAxis>
              <Tooltip
                formatter={(value, _name, item) => [
                  `${value} (${((item.payload.probability as number) * 100).toFixed(1)}%)`,
                  "Count",
                ]}
              />
              <Bar dataKey="count" fill="var(--accent)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="mt-2 text-xs text-[var(--text-secondary)]">
            Most frequent outcome: <span className="font-mono-tech font-medium text-[var(--text)]">{histogramData.slice().sort((a, b) => b.count - a.count)[0].bitstring}</span>{" "}
            ({histogramData.slice().sort((a, b) => b.count - a.count)[0].count} / {job.shots} shots)
          </p>
        </Card>
      )}

      {statevectorData.length > 0 && (
        <Card className="mb-4">
          <h2 className="mb-1 text-sm font-semibold text-[var(--text)]">Statevector probabilities</h2>
          <p className="mb-3 text-xs text-[var(--text-secondary)]">
            Exact amplitudes from the statevector simulator — not available from shot-based backends.
          </p>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={statevectorData} margin={{ left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="bitstring" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} domain={[0, 1]} />
              <Tooltip formatter={(value) => [Number(value).toFixed(4), "Probability"]} />
              <Bar dataKey="probability" fill="var(--accent)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {result && (
        <Card>
          <h2 className="mb-2 text-sm font-semibold text-[var(--text)]">Execution metadata</h2>
          <pre className="overflow-x-auto rounded-[var(--radius-md)] bg-[var(--surface-secondary)] p-3 font-mono-tech text-xs text-[var(--text)]">
            {JSON.stringify(result.execution_metadata, null, 2)}
          </pre>
        </Card>
      )}
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-xs text-[var(--text-secondary)]">{label}</p>
      <p className="mt-0.5 font-mono-tech text-sm font-medium text-[var(--text)]">{value}</p>
    </Card>
  );
}
