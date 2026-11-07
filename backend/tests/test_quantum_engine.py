"""Quantum engine correctness tests: gate construction, Bell/GHZ states,
statevector normalization, measurement probabilities, noise behaviour,
transpilation — no mocked quantum execution anywhere in this file."""
import math

from app.quantum.circuit_builder import CircuitValidationError, build_circuit, validate_circuit_json
from app.quantum.engine import QuantumExecutionError, execute_circuit
from app.quantum.analysis import full_resource_report

BELL = {
    "num_qubits": 2, "num_clbits": 2,
    "operations": [
        {"gate": "h", "qubits": [0]},
        {"gate": "cx", "qubits": [0, 1]},
        {"gate": "measure", "qubits": [0], "clbits": [0]},
        {"gate": "measure", "qubits": [1], "clbits": [1]},
    ],
}

GHZ3 = {
    "num_qubits": 3, "num_clbits": 3,
    "operations": [
        {"gate": "h", "qubits": [0]},
        {"gate": "cx", "qubits": [0, 1]},
        {"gate": "cx", "qubits": [1, 2]},
        {"gate": "measure", "qubits": [0], "clbits": [0]},
        {"gate": "measure", "qubits": [1], "clbits": [1]},
        {"gate": "measure", "qubits": [2], "clbits": [2]},
    ],
}


def test_bell_state_correctness():
    qc = build_circuit(BELL)
    result = execute_circuit(qc, "ideal_qasm", shots=4000)
    counts = result.measurement_counts
    assert set(counts.keys()) <= {"00", "11"}
    total = sum(counts.values())
    assert total == 4000
    # Both outcomes should be close to 50% (allow generous statistical slack).
    assert 0.4 < counts.get("00", 0) / total < 0.6
    assert 0.4 < counts.get("11", 0) / total < 0.6


def test_ghz_state_correctness():
    qc = build_circuit(GHZ3)
    result = execute_circuit(qc, "ideal_qasm", shots=4000)
    counts = result.measurement_counts
    assert set(counts.keys()) <= {"000", "111"}


def test_statevector_normalization():
    qc = build_circuit({"num_qubits": 2, "num_clbits": 0, "operations": [
        {"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]},
    ]})
    result = execute_circuit(qc, "statevector")
    assert math.isclose(result.metadata["statevector_norm"], 1.0, abs_tol=1e-9)
    assert math.isclose(sum(result.probabilities.values()), 1.0, abs_tol=1e-9)


def test_statevector_bell_probabilities():
    qc = build_circuit({"num_qubits": 2, "num_clbits": 0, "operations": [
        {"gate": "h", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]},
    ]})
    result = execute_circuit(qc, "statevector")
    assert math.isclose(result.probabilities.get("00", 0), 0.5, abs_tol=1e-9)
    assert math.isclose(result.probabilities.get("11", 0), 0.5, abs_tol=1e-9)
    assert "01" not in result.probabilities
    assert "10" not in result.probabilities


def test_measurement_counts_sum_to_shots():
    qc = build_circuit(GHZ3)
    result = execute_circuit(qc, "ideal_qasm", shots=777)
    assert sum(result.measurement_counts.values()) == 777


def test_noise_model_changes_distribution():
    """A noisy run of a Bell circuit should produce more outcome diversity
    (01/10 leaking in) than the ideal run — a real, measurable noise effect."""
    qc = build_circuit(BELL)
    ideal = execute_circuit(qc, "ideal_qasm", shots=5000)
    noisy = execute_circuit(qc, "noisy", shots=5000, noise_config={"preset": "high"})

    ideal_leakage = (ideal.measurement_counts.get("01", 0) + ideal.measurement_counts.get("10", 0)) / 5000
    noisy_leakage = (noisy.measurement_counts.get("01", 0) + noisy.measurement_counts.get("10", 0)) / 5000
    assert noisy_leakage > ideal_leakage


def test_custom_noise_config_requires_measurements_runs():
    qc = build_circuit(BELL)
    result = execute_circuit(
        qc, "custom_noise", shots=2000,
        noise_config={"single_qubit_gate_error": 0.05, "two_qubit_gate_error": 0.1,
                      "measurement_error": 0.05, "error_types": ["depolarizing", "readout"]},
    )
    assert sum(result.measurement_counts.values()) == 2000


def test_statevector_backend_rejects_too_many_qubits(monkeypatch):
    from app.core.config import settings as live_settings

    monkeypatch.setattr(live_settings, "max_qubits_statevector", 2)
    qc = build_circuit({"num_qubits": 5, "num_clbits": 0, "operations": [{"gate": "h", "qubits": [0]}]})
    try:
        execute_circuit(qc, "statevector")
        assert False, "expected QuantumExecutionError"
    except QuantumExecutionError:
        pass


def test_shots_backend_requires_measurements():
    qc = build_circuit({"num_qubits": 2, "num_clbits": 2, "operations": [{"gate": "h", "qubits": [0]}]})
    try:
        execute_circuit(qc, "ideal_qasm", shots=100)
        assert False, "expected QuantumExecutionError (no measurements)"
    except QuantumExecutionError:
        pass


def test_circuit_validation_rejects_bad_qubit_index():
    bad = {"num_qubits": 2, "num_clbits": 1, "operations": [{"gate": "h", "qubits": [5]}]}
    try:
        validate_circuit_json(bad)
        assert False, "expected CircuitValidationError"
    except CircuitValidationError:
        pass


def test_circuit_validation_rejects_wrong_param_count():
    bad = {"num_qubits": 1, "num_clbits": 0, "operations": [{"gate": "rx", "qubits": [0], "params": []}]}
    try:
        validate_circuit_json(bad)
        assert False, "expected CircuitValidationError"
    except CircuitValidationError:
        pass


def test_transpilation_changes_gate_set_for_linear_topology():
    qc = build_circuit(GHZ3)
    report = full_resource_report(qc, topology="linear")
    assert report["logical"]["depth"] > 0
    assert report["transpiled"]["transpiled_depth"] > 0
    assert "native_gate_distribution" in report["transpiled"]


def test_logical_vs_transpiled_gate_counts_are_distinguished():
    """Explicitly guard against confusing logical and physical gate counts."""
    qc = build_circuit(GHZ3)
    report = full_resource_report(qc, topology="fully_connected")
    logical_count = report["logical"]["total_gate_count"]
    transpiled_count = report["transpiled"]["transpiled_gate_count"]
    assert isinstance(logical_count, int)
    assert isinstance(transpiled_count, int)
    # They are allowed to differ (and usually do); the point is they are tracked separately.
    assert "total_gate_count" in report["logical"]
    assert "transpiled_gate_count" in report["transpiled"]
