"""Validate a structured JSON circuit description and build a Qiskit
QuantumCircuit from it. This is the ONLY path user input takes into the
quantum engine — no eval/exec of user-supplied code, ever.

Expected JSON shape:
{
  "num_qubits": 2,
  "num_clbits": 2,
  "operations": [
    {"gate": "h", "qubits": [0]},
    {"gate": "cx", "qubits": [0, 1]},
    {"gate": "rx", "qubits": [0], "params": [1.57]},
    {"gate": "measure", "qubits": [0], "clbits": [0]}
  ]
}
"""
from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

# Gate name -> (QuantumCircuit method name, number of qubits, number of params)
SINGLE_QUBIT_GATES: dict[str, tuple[str, int]] = {
    "id": ("id", 0),
    "x": ("x", 0),
    "y": ("y", 0),
    "z": ("z", 0),
    "h": ("h", 0),
    "s": ("s", 0),
    "t": ("t", 0),
    "rx": ("rx", 1),
    "ry": ("ry", 1),
    "rz": ("rz", 1),
}

MULTI_QUBIT_GATES: dict[str, tuple[str, int, int]] = {
    # name -> (method, n_qubits, n_params)
    "cx": ("cx", 2, 0),
    "cz": ("cz", 2, 0),
    "swap": ("swap", 2, 0),
    "crx": ("crx", 2, 1),
}

ALL_GATES = set(SINGLE_QUBIT_GATES) | set(MULTI_QUBIT_GATES)


class CircuitValidationError(ValueError):
    pass


def validate_circuit_json(config: dict[str, Any]) -> None:
    """Raise CircuitValidationError on any structural or semantic problem.

    Checked eagerly and explicitly instead of letting Qiskit raise an
    opaque error deep inside construction, so the API can return a
    clear 422 to the user.
    """
    if "num_qubits" not in config or "num_clbits" not in config or "operations" not in config:
        raise CircuitValidationError("Circuit JSON must contain num_qubits, num_clbits, operations")

    num_qubits = config["num_qubits"]
    num_clbits = config["num_clbits"]
    operations = config["operations"]

    if not isinstance(num_qubits, int) or num_qubits <= 0:
        raise CircuitValidationError("num_qubits must be a positive integer")
    if not isinstance(num_clbits, int) or num_clbits < 0:
        raise CircuitValidationError("num_clbits must be a non-negative integer")
    if not isinstance(operations, list):
        raise CircuitValidationError("operations must be a list")

    for i, op in enumerate(operations):
        if not isinstance(op, dict) or "gate" not in op or "qubits" not in op:
            raise CircuitValidationError(f"operations[{i}] must have 'gate' and 'qubits'")

        gate = op["gate"]
        qubits = op["qubits"]

        if not isinstance(qubits, list) or not all(isinstance(q, int) for q in qubits):
            raise CircuitValidationError(f"operations[{i}].qubits must be a list of integers")
        if any(q < 0 or q >= num_qubits for q in qubits):
            raise CircuitValidationError(f"operations[{i}] references a qubit index out of range [0, {num_qubits})")

        if gate == "measure":
            clbits = op.get("clbits")
            if not isinstance(clbits, list) or not all(isinstance(c, int) for c in clbits):
                raise CircuitValidationError(f"operations[{i}] (measure) must have integer 'clbits'")
            if len(clbits) != len(qubits):
                raise CircuitValidationError(f"operations[{i}] (measure) qubits/clbits length mismatch")
            if any(c < 0 or c >= num_clbits for c in clbits):
                raise CircuitValidationError(f"operations[{i}] references a clbit index out of range [0, {num_clbits})")
            continue

        condition = op.get("condition")
        if condition is not None:
            if not isinstance(condition, dict) or "clbit" not in condition or "equals" not in condition:
                raise CircuitValidationError(f"operations[{i}].condition must have 'clbit' and 'equals'")
            if not isinstance(condition["clbit"], int) or condition["clbit"] < 0 or condition["clbit"] >= num_clbits:
                raise CircuitValidationError(f"operations[{i}].condition.clbit out of range [0, {num_clbits})")
            if condition["equals"] not in (0, 1):
                raise CircuitValidationError(f"operations[{i}].condition.equals must be 0 or 1")

        if gate not in ALL_GATES:
            raise CircuitValidationError(f"operations[{i}] uses unknown gate '{gate}'. Allowed: {sorted(ALL_GATES)}")

        if gate in SINGLE_QUBIT_GATES:
            _, n_params = SINGLE_QUBIT_GATES[gate]
            if len(qubits) != 1:
                raise CircuitValidationError(f"operations[{i}] ('{gate}') expects exactly 1 qubit")
        else:
            _, n_qubits_expected, n_params = MULTI_QUBIT_GATES[gate]
            if len(qubits) != n_qubits_expected:
                raise CircuitValidationError(f"operations[{i}] ('{gate}') expects exactly {n_qubits_expected} qubits")

        params = op.get("params", [])
        if not isinstance(params, list) or len(params) != n_params:
            raise CircuitValidationError(f"operations[{i}] ('{gate}') expects {n_params} numeric params")
        if not all(isinstance(p, (int, float)) for p in params):
            raise CircuitValidationError(f"operations[{i}] ('{gate}') params must be numeric")


def build_circuit(config: dict[str, Any]) -> QuantumCircuit:
    """Validate and construct a Qiskit QuantumCircuit from JSON. Raises
    CircuitValidationError on any invalid input."""
    validate_circuit_json(config)

    qc = QuantumCircuit(config["num_qubits"], config["num_clbits"])

    for op in config["operations"]:
        gate = op["gate"]
        qubits = op["qubits"]

        if gate == "measure":
            qc.measure(qubits, op["clbits"])
            continue

        params = op.get("params", [])
        if gate in SINGLE_QUBIT_GATES:
            method_name, _ = SINGLE_QUBIT_GATES[gate]
        else:
            method_name, _, _ = MULTI_QUBIT_GATES[gate]

        condition = op.get("condition")
        if condition is not None:
            with qc.if_test((qc.clbits[condition["clbit"]], condition["equals"])):
                getattr(qc, method_name)(*params, *qubits)
        else:
            getattr(qc, method_name)(*params, *qubits)

    return qc


def circuit_has_measurements(config: dict[str, Any]) -> bool:
    return any(op.get("gate") == "measure" for op in config.get("operations", []))
