"""Build Qiskit Aer NoiseModel objects from a simple JSON noise config.

Supported noise types, matching the project brief:
- depolarizing error (single- and two-qubit gates)
- bit-flip / phase-flip (Pauli) error
- amplitude damping
- readout error

Config shape:
{
  "single_qubit_gate_error": 0.01,
  "two_qubit_gate_error": 0.02,
  "measurement_error": 0.01,
  "error_types": ["depolarizing", "bit_flip", "phase_flip", "amplitude_damping", "readout"]
}
"""
from __future__ import annotations

from typing import Any

from qiskit_aer.noise import (
    NoiseModel,
    ReadoutError,
    amplitude_damping_error,
    depolarizing_error,
    pauli_error,
)

SINGLE_QUBIT_GATE_NAMES = ["id", "x", "y", "z", "h", "s", "t", "rx", "ry", "rz"]
TWO_QUBIT_GATE_NAMES = ["cx", "cz", "swap", "crx"]


def build_noise_model(config: dict[str, Any] | None) -> NoiseModel | None:
    """Return a NoiseModel built from `config`, or None for an ideal (noiseless) run."""
    if not config:
        return None

    noise_model = NoiseModel()
    error_types = set(config.get("error_types", ["depolarizing"]))

    p1 = float(config.get("single_qubit_gate_error", 0.0))
    p2 = float(config.get("two_qubit_gate_error", 0.0))
    p_meas = float(config.get("measurement_error", 0.0))

    if "depolarizing" in error_types and p1 > 0:
        err1 = depolarizing_error(p1, 1)
        noise_model.add_all_qubit_quantum_error(err1, SINGLE_QUBIT_GATE_NAMES)
    if "depolarizing" in error_types and p2 > 0:
        err2 = depolarizing_error(p2, 2)
        noise_model.add_all_qubit_quantum_error(err2, TWO_QUBIT_GATE_NAMES)

    if "bit_flip" in error_types and p1 > 0:
        err_bf = pauli_error([("X", p1), ("I", 1 - p1)])
        noise_model.add_all_qubit_quantum_error(err_bf, SINGLE_QUBIT_GATE_NAMES)

    if "phase_flip" in error_types and p1 > 0:
        err_pf = pauli_error([("Z", p1), ("I", 1 - p1)])
        noise_model.add_all_qubit_quantum_error(err_pf, SINGLE_QUBIT_GATE_NAMES)

    if "amplitude_damping" in error_types and p1 > 0:
        err_ad = amplitude_damping_error(p1)
        noise_model.add_all_qubit_quantum_error(err_ad, SINGLE_QUBIT_GATE_NAMES)

    if "readout" in error_types and p_meas > 0:
        ro_error = ReadoutError([[1 - p_meas, p_meas], [p_meas, 1 - p_meas]])
        noise_model.add_all_qubit_readout_error(ro_error)

    return noise_model


PRESET_NOISE_LEVELS: dict[str, dict[str, Any]] = {
    "low": {"single_qubit_gate_error": 0.001, "two_qubit_gate_error": 0.01, "measurement_error": 0.01,
            "error_types": ["depolarizing", "readout"]},
    "medium": {"single_qubit_gate_error": 0.01, "two_qubit_gate_error": 0.03, "measurement_error": 0.03,
               "error_types": ["depolarizing", "readout"]},
    "high": {"single_qubit_gate_error": 0.03, "two_qubit_gate_error": 0.08, "measurement_error": 0.05,
             "error_types": ["depolarizing", "readout"]},
}
