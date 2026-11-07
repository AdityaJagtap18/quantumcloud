"""The quantum execution engine: a backend abstraction over Qiskit Aer.

Four backend types (matching the project brief):
  - ideal_qasm:   shot-based, noiseless, returns measurement counts
  - statevector:  returns final statevector + probabilities, no noise
  - noisy:        shot-based with a noise model (preset or custom)
  - custom_noise: shot-based with a fully user-specified noise config

All of these are CPU simulations via qiskit-aer's AerSimulator. None of
this talks to real quantum hardware — see BackendInfo.backend_type and
the README for why that distinction matters.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator

from app.core.config import settings
from app.quantum.noise_models import PRESET_NOISE_LEVELS, build_noise_model


class QuantumExecutionError(RuntimeError):
    pass


@dataclass
class ExecutionResult:
    backend_name: str
    shots: int | None
    measurement_counts: dict[str, int] | None
    probabilities: dict[str, float] | None
    statevector: dict[str, list[float]] | None  # {"real": [...], "imag": [...]}
    execution_time_seconds: float
    transpile_time_seconds: float
    metadata: dict[str, Any]


BACKEND_REGISTRY: dict[str, dict[str, Any]] = {
    "ideal_qasm": {
        "name": "Ideal QASM Simulator",
        "backend_type": "ideal_qasm",
        "description": "Noiseless shot-based simulation returning measurement counts.",
        "requires_measurements": True,
    },
    "statevector": {
        "name": "Statevector Simulator",
        "backend_type": "statevector",
        "description": "Returns the exact final statevector and probabilities. No noise, no shots.",
        "requires_measurements": False,
    },
    "noisy": {
        "name": "Noisy Simulator",
        "backend_type": "noisy",
        "description": "Shot-based simulation with a hardware-inspired noise model (preset or custom).",
        "requires_measurements": True,
    },
    "custom_noise": {
        "name": "Custom Noise Configuration",
        "backend_type": "custom_noise",
        "description": "Shot-based simulation with a fully user-specified noise configuration.",
        "requires_measurements": True,
    },
}


def list_backends() -> list[dict[str, Any]]:
    return [{"id": key, **value} for key, value in BACKEND_REGISTRY.items()]


def _check_qubit_limits(num_qubits: int, backend_type: str) -> None:
    if backend_type == "statevector":
        if num_qubits > settings.max_qubits_statevector:
            raise QuantumExecutionError(
                f"Statevector simulation requires 2^n complex amplitudes; "
                f"{num_qubits} qubits exceeds the configured limit of "
                f"{settings.max_qubits_statevector} qubits."
            )
    else:
        if num_qubits > settings.max_qubits_shots:
            raise QuantumExecutionError(
                f"{num_qubits} qubits exceeds the configured limit of {settings.max_qubits_shots} qubits."
            )


def execute_circuit(
    circuit: QuantumCircuit,
    backend_type: str,
    shots: int = 1024,
    noise_config: dict[str, Any] | None = None,
) -> ExecutionResult:
    """Run `circuit` on the named backend type and return a structured result."""
    if backend_type not in BACKEND_REGISTRY:
        raise QuantumExecutionError(f"Unknown backend type '{backend_type}'")

    _check_qubit_limits(circuit.num_qubits, backend_type)

    if shots > settings.max_shots:
        raise QuantumExecutionError(f"shots={shots} exceeds the configured limit of {settings.max_shots}")

    if backend_type == "statevector":
        return _run_statevector(circuit)

    noise_model = None
    if backend_type == "noisy":
        preset = (noise_config or {}).get("preset", "medium")
        noise_model = build_noise_model(PRESET_NOISE_LEVELS.get(preset, PRESET_NOISE_LEVELS["medium"]))
    elif backend_type == "custom_noise":
        noise_model = build_noise_model(noise_config)

    return _run_shots(circuit, shots, noise_model, backend_type)


def _run_statevector(circuit: QuantumCircuit) -> ExecutionResult:
    sim = AerSimulator(method="statevector")
    qc = circuit.copy()
    qc.save_statevector()

    start_t = time.perf_counter()
    tqc = transpile(qc, sim)
    transpile_time = time.perf_counter() - start_t

    start_e = time.perf_counter()
    job = sim.run(tqc)
    result = job.result()
    exec_time = time.perf_counter() - start_e

    sv: Statevector = result.get_statevector()
    amplitudes = sv.data
    probs = {format(i, f"0{circuit.num_qubits}b"): float(abs(amp) ** 2) for i, amp in enumerate(amplitudes) if abs(amp) ** 2 > 1e-12}

    norm = float(sum(abs(a) ** 2 for a in amplitudes))

    return ExecutionResult(
        backend_name=BACKEND_REGISTRY["statevector"]["name"],
        shots=None,
        measurement_counts=None,
        probabilities=probs,
        statevector={"real": amplitudes.real.tolist(), "imag": amplitudes.imag.tolist()},
        execution_time_seconds=exec_time,
        transpile_time_seconds=transpile_time,
        metadata={"statevector_norm": norm, "num_qubits": circuit.num_qubits},
    )


def _run_shots(
    circuit: QuantumCircuit, shots: int, noise_model, backend_type: str
) -> ExecutionResult:
    has_measurement = any(instr.operation.name == "measure" for instr in circuit.data)
    if not circuit.clbits or not has_measurement:
        raise QuantumExecutionError("Shot-based backends require at least one measurement operation.")

    sim = AerSimulator(noise_model=noise_model) if noise_model else AerSimulator()

    start_t = time.perf_counter()
    tqc = transpile(circuit, sim)
    transpile_time = time.perf_counter() - start_t

    start_e = time.perf_counter()
    job = sim.run(tqc, shots=shots)
    result = job.result()
    exec_time = time.perf_counter() - start_e

    counts = result.get_counts()
    total = sum(counts.values())
    probabilities = {bitstring: count / total for bitstring, count in counts.items()}

    return ExecutionResult(
        backend_name=BACKEND_REGISTRY[backend_type]["name"],
        shots=shots,
        measurement_counts=dict(counts),
        probabilities=probabilities,
        statevector=None,
        execution_time_seconds=exec_time,
        transpile_time_seconds=transpile_time,
        metadata={"noisy": noise_model is not None, "num_qubits": circuit.num_qubits},
    )
