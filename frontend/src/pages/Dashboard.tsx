import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { dashboardApi } from "../api/endpoints";
import type { DashboardStats } from "../types";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Table, THead, Th, Td, Tr } from "../components/ui/Table";

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
      <p className="mt-1.5 font-mono-tech text-xl font-semibold text-[var(--text)]">{value}</p>
    </Card>
  );
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    dashboardApi
      .stats()
      .then((r) => setStats(r.data))
      .catch(() => setError("Failed to load dashboard statistics."));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!stats) return <LoadingState label="Loading dashboard" />;

  return (
    <div>
      <PageHeader title="Overview" description="Execution activity across your quantum jobs." />

      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="Total jobs" value={stats.total_jobs} />
        <StatCard label="Completed" value={stats.completed_jobs} />
        <StatCard label="Running" value={stats.running_jobs} />
        <StatCard label="Queued" value={stats.queued_jobs} />
        <StatCard label="Failed" value={stats.failed_jobs} />
      </div>

      <Card className="mb-6">
        <p className="text-xs font-medium text-[var(--text-secondary)]">Average execution time</p>
        <p className="mt-1.5 font-mono-tech text-xl font-semibold text-[var(--text)]">
          {stats.average_execution_time_seconds !== null
            ? `${stats.average_execution_time_seconds.toFixed(4)}s`
            : "—"}
        </p>
      </Card>

      <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Recent executions</h2>
      {stats.recent_jobs.length === 0 ? (
        <EmptyState title="No jobs yet" hint="Head to Circuit Lab to build and submit your first quantum job." />
      ) : (
        <Table>
          <THead>
            <Th>Job ID</Th>
            <Th>Status</Th>
            <Th>Submitted</Th>
            <Th>Execution time</Th>
          </THead>
          <tbody>
            {stats.recent_jobs.map((j) => (
              <Tr key={j.id} onClick={() => navigate(`/jobs/${j.id}`)}>
                <Td mono>{j.id.slice(0, 8)}</Td>
                <Td><StatusBadge status={j.status} /></Td>
                <Td>{new Date(j.submitted_at).toLocaleString()}</Td>
                <Td mono>{j.execution_time !== null ? `${j.execution_time.toFixed(4)}s` : "—"}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
