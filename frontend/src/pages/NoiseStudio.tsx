import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Legend, Label as RLabel } from "recharts";
import { backendsApi, experimentsApi } from "../api/endpoints";
import type { CircuitConfig, ExperimentRun } from "../types";
import { CircuitEditor } from "../components/CircuitEditor";
import { ErrorState, EmptyState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Input, Label } from "../components/ui/Input";
import { Table, THead, Th, Td, Tr } from "../components/ui/Table";

const BELL_CIRCUIT: CircuitConfig = {
  num_qubits: 2,
  num_clbits: 2,
  operations: [
    { gate: "h", qubits: [0] },
    { gate: "cx", qubits: [0, 1] },
    { gate: "measure", qubits: [0], clbits: [0] },
    { gate: "measure", qubits: [1], clbits: [1] },
  ],
};

const DEFAULT_LEVELS = "0.0, 0.01, 0.03, 0.05, 0.10";

export function NoiseStudio() {
  const [circuit, setCircuit] = useState<CircuitConfig>(BELL_CIRCUIT);
  const [levelsText, setLevelsText] = useState(DEFAULT_LEVELS);
  const [shots, setShots] = useState(2000);
  const [runs, setRuns] = useState<ExperimentRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function handleRunSweep() {
    setError(null);
    setRunning(true);
    setRuns(null);
    try {
      const noiseLevels = levelsText
        .split(",")
        .map((s) => parseFloat(s.trim()))
        .filter((n) => !Number.isNaN(n));

      const backendsResp = await backendsApi.list();
      const idealBackend = backendsResp.data.find((b) => b.backend_type === "ideal_qasm");
      if (!idealBackend) throw new Error("No ideal backend available");

      const createResp = await experimentsApi.create({
        experiment_name: `noise-sweep-${Date.now()}`,
        circuit,
        backend_id: idealBackend.id,
        shots,
        noise_levels: noiseLevels,
      });

      const detailResp = await experimentsApi.get(createResp.data.id);
      setRuns(detailResp.data.runs.sort((a, b) => a.noise_level - b.noise_level));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } }; message?: string });
      setError(detail?.response?.data?.detail || detail?.message || "Noise sweep failed");
    } finally {
      setRunning(false);
    }
  }

  const chartData = runs?.map((r) => ({
    noise_level: r.noise_level,
    fidelity_proxy: r.metrics.fidelity_proxy,
    observable_error: r.metrics.observable_error,
  }));

  return (
    <div>
      <PageHeader
        title="Experiments"
        description="Run a circuit across several noise levels and compare measurement distributions against the ideal, noiseless baseline."
      />

      <Card className="mb-4">
        <CircuitEditor circuit={circuit} onChange={setCircuit} />
      </Card>

      <Card className="mb-4">
        <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Experiment configuration</h2>
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-80">
            <Label>Noise levels (comma-separated, depolarizing + readout error probability)</Label>
            <Input value={levelsText} onChange={(e) => setLevelsText(e.target.value)} />
          </div>
          <div className="w-28">
            <Label>Shots per level</Label>
            <Input type="number" value={shots} onChange={(e) => setShots(Number(e.target.value))} />
          </div>
          <Button variant="primary" onClick={handleRunSweep} disabled={running}>
            {running ? "Running sweep..." : "Run noise sweep"}
          </Button>
        </div>
      </Card>

      {error && <ErrorState message={error} />}

      {!runs && !running && !error && (
        <EmptyState title="No sweep run yet" hint="Configure a circuit and noise levels above, then run the sweep." />
      )}

      {chartData && chartData.length > 0 && (
        <>
          <Card className="mb-4">
            <h2 className="mb-1 text-sm font-semibold text-[var(--text)]">Fidelity and observable error vs. noise level</h2>
            <p className="mb-3 text-xs text-[var(--text-secondary)]">
              Fidelity proxy = 1 − total variation distance between the noisy and ideal measurement distributions
              (a shot-based estimate, not a true quantum state fidelity).
            </p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData} margin={{ left: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="noise_level" tick={{ fontSize: 11, fill: "var(--text-secondary)" }}>
                  <RLabel value="Noise probability" offset={-4} position="insideBottom" fill="var(--text-muted)" fontSize={10} />
                </XAxis>
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
                <Tooltip />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="fidelity_proxy" stroke="var(--accent)" name="Fidelity (proxy)" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="observable_error" stroke="var(--warning)" name="Observable error (TVD)" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Run detail</h2>
            <Table>
              <THead>
                <Th>Noise level</Th>
                <Th>Fidelity (proxy)</Th>
                <Th>Observable error</Th>
                <Th>Execution time</Th>
              </THead>
              <tbody>
                {runs!.map((r) => (
                  <Tr key={r.id}>
                    <Td mono>{r.noise_level}</Td>
                    <Td mono>{r.metrics.fidelity_proxy.toFixed(4)}</Td>
                    <Td mono>{r.metrics.observable_error.toFixed(4)}</Td>
                    <Td mono>{(r.metrics.execution_time_seconds * 1000).toFixed(1)} ms</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </Card>
        </>
      )}
    </div>
  );
}
