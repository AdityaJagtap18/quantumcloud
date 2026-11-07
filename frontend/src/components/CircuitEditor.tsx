import { useState } from "react";
import type { CircuitConfig, CircuitOperation } from "../types";
import { Button } from "./ui/Button";
import { Label, Select } from "./ui/Input";

const SINGLE_QUBIT_GATES = ["id", "x", "y", "z", "h", "s", "t"];
const ROTATION_GATES = ["rx", "ry", "rz"];
const TWO_QUBIT_GATES = ["cx", "cz", "swap"];
const CONTROLLED_ROTATION_GATES = ["crx"];

interface Props {
  circuit: CircuitConfig;
  onChange: (circuit: CircuitConfig) => void;
}

export function CircuitEditor({ circuit, onChange }: Props) {
  const [gateType, setGateType] = useState("h");
  const [qubitA, setQubitA] = useState(0);
  const [qubitB, setQubitB] = useState(1);
  const [clbit, setClbit] = useState(0);
  const [angle, setAngle] = useState(Math.PI / 2);

  function updateCircuit(next: Partial<CircuitConfig>) {
    onChange({ ...circuit, ...next });
  }

  function addQubit() {
    updateCircuit({ num_qubits: circuit.num_qubits + 1 });
  }

  function removeQubit() {
    if (circuit.num_qubits <= 1) return;
    const newN = circuit.num_qubits - 1;
    updateCircuit({
      num_qubits: newN,
      operations: circuit.operations.filter((op) => op.qubits.every((q) => q < newN)),
    });
  }

  function addClbit() {
    updateCircuit({ num_clbits: circuit.num_clbits + 1 });
  }

  function removeClbit() {
    if (circuit.num_clbits <= 0) return;
    const newN = circuit.num_clbits - 1;
    updateCircuit({
      num_clbits: newN,
      operations: circuit.operations.filter((op) => !op.clbits || op.clbits.every((c) => c < newN)),
    });
  }

  function addOperation() {
    let op: CircuitOperation;
    if (gateType === "measure") {
      if (circuit.num_clbits === 0) return;
      op = { gate: "measure", qubits: [qubitA], clbits: [clbit] };
    } else if (SINGLE_QUBIT_GATES.includes(gateType)) {
      op = { gate: gateType, qubits: [qubitA] };
    } else if (ROTATION_GATES.includes(gateType)) {
      op = { gate: gateType, qubits: [qubitA], params: [angle] };
    } else if (TWO_QUBIT_GATES.includes(gateType)) {
      if (qubitA === qubitB) return;
      op = { gate: gateType, qubits: [qubitA, qubitB] };
    } else if (CONTROLLED_ROTATION_GATES.includes(gateType)) {
      if (qubitA === qubitB) return;
      op = { gate: gateType, qubits: [qubitA, qubitB], params: [angle] };
    } else {
      return;
    }
    updateCircuit({ operations: [...circuit.operations, op] });
  }

  function removeOperation(index: number) {
    updateCircuit({ operations: circuit.operations.filter((_, i) => i !== index) });
  }

  function clearAll() {
    updateCircuit({ operations: [] });
  }

  const needsAngle = ROTATION_GATES.includes(gateType) || CONTROLLED_ROTATION_GATES.includes(gateType);
  const needsSecondQubit = TWO_QUBIT_GATES.includes(gateType) || CONTROLLED_ROTATION_GATES.includes(gateType);
  const needsClbit = gateType === "measure";

  return (
    <div>
      {/* Toolbar */}
      <div className="mb-3 flex flex-wrap items-end gap-3 rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface-secondary)] p-3">
        <div>
          <Label>Qubits</Label>
          <div className="flex items-center gap-1">
            <Button size="sm" onClick={removeQubit}>−</Button>
            <span className="w-6 text-center text-sm font-mono-tech">{circuit.num_qubits}</span>
            <Button size="sm" onClick={addQubit}>+</Button>
          </div>
        </div>

        <div>
          <Label>Classical bits</Label>
          <div className="flex items-center gap-1">
            <Button size="sm" onClick={removeClbit}>−</Button>
            <span className="w-6 text-center text-sm font-mono-tech">{circuit.num_clbits}</span>
            <Button size="sm" onClick={addClbit}>+</Button>
          </div>
        </div>

        <div>
          <Label>Gate</Label>
          <Select value={gateType} onChange={(e) => setGateType(e.target.value)} className="w-36">
            <optgroup label="Single-qubit">
              {SINGLE_QUBIT_GATES.map((g) => (
                <option key={g} value={g}>{g.toUpperCase()}</option>
              ))}
            </optgroup>
            <optgroup label="Rotation">
              {ROTATION_GATES.map((g) => (
                <option key={g} value={g}>{g.toUpperCase()}(θ)</option>
              ))}
            </optgroup>
            <optgroup label="Two-qubit">
              {TWO_QUBIT_GATES.map((g) => (
                <option key={g} value={g}>{g.toUpperCase()}</option>
              ))}
            </optgroup>
            <optgroup label="Controlled rotation">
              {CONTROLLED_ROTATION_GATES.map((g) => (
                <option key={g} value={g}>{g.toUpperCase()}(θ)</option>
              ))}
            </optgroup>
            <optgroup label="Measurement">
              <option value="measure">Measure</option>
            </optgroup>
          </Select>
        </div>

        <div>
          <Label>{needsSecondQubit ? "Control qubit" : "Qubit"}</Label>
          <Select value={qubitA} onChange={(e) => setQubitA(Number(e.target.value))} className="w-16">
            {Array.from({ length: circuit.num_qubits }, (_, i) => (
              <option key={i} value={i}>q{i}</option>
            ))}
          </Select>
        </div>

        {needsSecondQubit && (
          <div>
            <Label>Target qubit</Label>
            <Select value={qubitB} onChange={(e) => setQubitB(Number(e.target.value))} className="w-16">
              {Array.from({ length: circuit.num_qubits }, (_, i) => (
                <option key={i} value={i}>q{i}</option>
              ))}
            </Select>
          </div>
        )}

        {needsClbit && (
          <div>
            <Label>Classical bit</Label>
            <Select value={clbit} onChange={(e) => setClbit(Number(e.target.value))} className="w-16">
              {Array.from({ length: circuit.num_clbits }, (_, i) => (
                <option key={i} value={i}>c{i}</option>
              ))}
            </Select>
          </div>
        )}

        {needsAngle && (
          <div>
            <Label>Angle (rad)</Label>
            <input
              type="number"
              step="0.01"
              value={angle}
              onChange={(e) => setAngle(Number(e.target.value))}
              className="h-8 w-24 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-2 text-sm font-mono-tech outline-none focus:border-[var(--accent)]"
            />
          </div>
        )}

        <Button variant="primary" onClick={addOperation}>Add gate</Button>
        <Button onClick={clearAll}>Clear</Button>
      </div>

      {/* Wire visualization */}
      <div className="overflow-x-auto rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface)] p-4">
        {Array.from({ length: circuit.num_qubits }, (_, q) => (
          <div key={q} className="mb-2 flex items-center">
            <span className="w-10 shrink-0 font-mono-tech text-xs text-[var(--text-muted)]">q{q}</span>
            <div className="relative flex h-9 flex-1 items-center">
              <div className="absolute inset-x-0 top-1/2 h-px bg-[var(--border)]" />
              <div className="flex gap-2">
                {circuit.operations.map((op, i) =>
                  op.qubits.includes(q) ? (
                    <button
                      key={i}
                      onClick={() => removeOperation(i)}
                      title="Click to remove"
                      className={`relative z-10 flex h-7 min-w-7 items-center justify-center rounded-[var(--radius-sm)] border px-1.5 font-mono-tech text-xs font-medium ${
                        op.gate === "measure"
                          ? "border-[var(--warning)]/40 bg-[var(--warning-bg)] text-[var(--warning)]"
                          : "border-[var(--accent)]/40 bg-[var(--accent)]/10 text-[var(--accent)]"
                      }`}
                    >
                      {op.gate === "measure" ? "M" : op.gate.toUpperCase()}
                      {op.qubits.length === 2 && (op.qubits[0] === q ? " ●" : " ○")}
                    </button>
                  ) : null
                )}
              </div>
            </div>
          </div>
        ))}
        {circuit.operations.length === 0 && (
          <p className="py-6 text-center text-sm text-[var(--text-muted)]">
            No gates yet — use the toolbar above to build your circuit.
          </p>
        )}
      </div>
    </div>
  );
}
