import { PageHeader } from "../components/ui/PageHeader";
import { Card } from "../components/ui/Card";

const SECTIONS = [
  {
    title: "Quantum execution lifecycle",
    body: "A submitted job moves through QUEUED → VALIDATING → RUNNING → COMPLETED / FAILED / CANCELLED. Submission only validates and enqueues the circuit — the API never blocks on simulation.",
  },
  {
    title: "Backends",
    body: "Four simulator backends are available: ideal_qasm (noiseless, shot-based), statevector (exact amplitudes, no noise), noisy (preset noise levels), and custom_noise (fully configurable depolarizing/readout/amplitude-damping error). None of these are physical hardware.",
  },
  {
    title: "Circuit JSON schema",
    body: "{ num_qubits, num_clbits, operations: [{ gate, qubits, clbits?, params?, condition? }] }. Gate names and parameter counts are validated server-side before a circuit is constructed; unsupported gates or malformed operations are rejected with a specific error.",
  },
  {
    title: "Resource limits",
    body: "Statevector simulation is capped at 20 qubits (memory grows as 2^n); shot-based backends are capped at 30 qubits and 100,000 shots per job. These limits are enforced before a job is queued.",
  },
  {
    title: "Noise studio methodology",
    body: "A noise sweep runs a 4000-shot ideal baseline once, then one execution per requested noise level. The reported fidelity_proxy is 1 minus the total variation distance between the noisy and ideal measurement distributions — a shot-statistics proxy, not a true quantum state fidelity.",
  },
];

export function Documentation() {
  return (
    <div>
      <PageHeader title="Documentation" description="Reference notes on how QuantumCloud's execution model works." />
      <div className="flex flex-col gap-3">
        {SECTIONS.map((s) => (
          <Card key={s.title}>
            <h2 className="mb-1.5 text-sm font-semibold text-[var(--text)]">{s.title}</h2>
            <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{s.body}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
