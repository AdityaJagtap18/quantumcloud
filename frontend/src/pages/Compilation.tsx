import { useState } from "react";
import { circuitsApi } from "../api/endpoints";
import type { CircuitConfig, ResourceReport } from "../types";
import { CircuitEditor } from "../components/CircuitEditor";
import { ErrorState, EmptyState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Label, Select } from "../components/ui/Input";
import { Table, THead, Th, Td, Tr } from "../components/ui/Table";

const DEFAULT_CIRCUIT: CircuitConfig = {
  num_qubits: 3,
  num_clbits: 3,
  operations: [
    { gate: "h", qubits: [0] },
    { gate: "cx", qubits: [0, 1] },
    { gate: "cx", qubits: [1, 2] },
    { gate: "measure", qubits: [0], clbits: [0] },
    { gate: "measure", qubits: [1], clbits: [1] },
    { gate: "measure", qubits: [2], clbits: [2] },
  ],
};

export function Compilation() {
  const [circuit, setCircuit] = useState<CircuitConfig>(DEFAULT_CIRCUIT);
  const [topology, setTopology] = useState("linear");
  const [report, setReport] = useState<ResourceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    setError(null);
    setLoading(true);
    try {
      const resp = await circuitsApi.analyze(circuit, topology);
      setReport(resp.data);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Compilation analysis failed");
      setReport(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Compilation"
        description="Compare a circuit's logical structure against its physical form after transpilation to a target hardware topology."
      />

      <Card className="mb-4">
        <CircuitEditor circuit={circuit} onChange={setCircuit} />
      </Card>

      <Card className="mb-4">
        <div className="flex items-end gap-3">
          <div className="w-48">
            <Label>Hardware topology</Label>
            <Select value={topology} onChange={(e) => setTopology(e.target.value)}>
              <option value="fully_connected">Fully connected</option>
              <option value="linear">Linear chain</option>
              <option value="ring">Ring</option>
              <option value="heavy_hex_like">Heavy-hex-like</option>
            </Select>
          </div>
          <Button variant="primary" onClick={handleAnalyze} disabled={loading}>
            {loading ? "Compiling..." : "Compile"}
          </Button>
        </div>
      </Card>

      {error && <ErrorState message={error} />}

      {!report && !error && (
        <EmptyState title="No compilation run yet" hint="Build a circuit above and click Compile." />
      )}

      {report && (
        <Card>
          <Table>
            <THead>
              <Th>Metric</Th>
              <Th>Logical (original)</Th>
              <Th>Transpiled ({report.transpiled.topology})</Th>
            </THead>
            <tbody>
              <Tr>
                <Td>Qubits</Td>
                <Td mono>{report.logical.num_qubits}</Td>
                <Td mono>—</Td>
              </Tr>
              <Tr>
                <Td>Depth</Td>
                <Td mono>{report.logical.depth}</Td>
                <Td mono>{report.transpiled.transpiled_depth}</Td>
              </Tr>
              <Tr>
                <Td>Total gate count</Td>
                <Td mono>{report.logical.total_gate_count}</Td>
                <Td mono>{report.transpiled.transpiled_gate_count}</Td>
              </Tr>
              <Tr>
                <Td>Single-qubit gates</Td>
                <Td mono>{report.logical.single_qubit_gate_count}</Td>
                <Td mono>—</Td>
              </Tr>
              <Tr>
                <Td>Two-qubit gates</Td>
                <Td mono>{report.logical.two_qubit_gate_count}</Td>
                <Td mono>—</Td>
              </Tr>
              <Tr>
                <Td>SWAP overhead</Td>
                <Td mono>—</Td>
                <Td mono>{report.transpiled.swap_gate_overhead}</Td>
              </Tr>
              <Tr>
                <Td>Resource overhead ratio</Td>
                <Td mono>—</Td>
                <Td mono>{report.transpiled.resource_overhead_ratio?.toFixed(2) ?? "—"}</Td>
              </Tr>
              <Tr>
                <Td>Transpile time</Td>
                <Td mono>—</Td>
                <Td mono>{(report.transpiled.transpile_time_seconds * 1000).toFixed(2)} ms</Td>
              </Tr>
            </tbody>
          </Table>

          <p className="mt-4 text-xs font-medium text-[var(--text-secondary)]">Native gate distribution</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.entries(report.transpiled.native_gate_distribution).map(([gate, count]) => (
              <span
                key={gate}
                className="rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-secondary)] px-2 py-1 font-mono-tech text-xs text-[var(--text)]"
              >
                {gate}: {count}
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
