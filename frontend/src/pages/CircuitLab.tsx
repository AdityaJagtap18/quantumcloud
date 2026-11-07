import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { backendsApi, circuitsApi, jobsApi } from "../api/endpoints";
import type { BackendInfo, CircuitConfig } from "../types";
import { CircuitEditor } from "../components/CircuitEditor";
import { ErrorState } from "../components/States";
import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Label, Select, Input } from "../components/ui/Input";

const DEFAULT_CIRCUIT: CircuitConfig = {
  num_qubits: 2,
  num_clbits: 2,
  operations: [
    { gate: "h", qubits: [0] },
    { gate: "cx", qubits: [0, 1] },
    { gate: "measure", qubits: [0], clbits: [0] },
    { gate: "measure", qubits: [1], clbits: [1] },
  ],
};

export function CircuitLab() {
  const location = useLocation() as { state?: { preloadedCircuit?: CircuitConfig } };
  const navigate = useNavigate();

  const [circuit, setCircuit] = useState<CircuitConfig>(location.state?.preloadedCircuit ?? DEFAULT_CIRCUIT);
  const [backends, setBackends] = useState<BackendInfo[]>([]);
  const [backendId, setBackendId] = useState("");
  const [shots, setShots] = useState(1024);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<{ valid: boolean; error: string | null } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    backendsApi.list().then((r) => {
      setBackends(r.data);
      if (r.data.length > 0) setBackendId(r.data[0].id);
    });
  }, []);

  const selectedBackend = backends.find((b) => b.id === backendId);
  const requiresMeasurements = selectedBackend?.requires_measurements ?? true;

  async function handleValidate() {
    setValidating(true);
    try {
      const resp = await circuitsApi.validate(circuit);
      setValidation(resp.data);
    } finally {
      setValidating(false);
    }
  }

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      const resp = await jobsApi.submit(circuit, backendId, shots);
      navigate(`/jobs/${resp.data.id}`);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Job submission failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="Circuit Lab" description="Build a quantum circuit and submit it for execution." />

      <Card className="mb-4">
        <CircuitEditor
          circuit={{ ...circuit }}
          onChange={(c) => {
            setCircuit(c);
            setValidation(null);
          }}
        />
      </Card>

      <div className="mb-4 flex items-center gap-2">
        <Button size="sm" onClick={handleValidate} disabled={validating}>
          {validating ? "Validating..." : "Validate circuit"}
        </Button>
        {validation && (
          <span
            className={`text-xs font-medium ${validation.valid ? "text-[var(--success)]" : "text-[var(--error)]"}`}
          >
            {validation.valid ? "Circuit is valid" : validation.error}
          </span>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <ErrorState message={error} />
        </div>
      )}

      <Card className="max-w-md">
        <h2 className="mb-3 text-sm font-semibold text-[var(--text)]">Execution</h2>

        <div className="mb-3">
          <Label>Backend</Label>
          <Select value={backendId} onChange={(e) => setBackendId(e.target.value)}>
            {backends.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </Select>
        </div>
        {selectedBackend && <p className="mb-3 text-xs text-[var(--text-secondary)]">{selectedBackend.description}</p>}

        {requiresMeasurements && (
          <div className="mb-4">
            <Label>Shots</Label>
            <Input type="number" min={1} max={100000} value={shots} onChange={(e) => setShots(Number(e.target.value))} />
          </div>
        )}

        <Button variant="primary" onClick={handleSubmit} disabled={submitting || !backendId} className="w-full">
          {submitting ? "Submitting..." : "Execute circuit"}
        </Button>
      </Card>
    </div>
  );
}
