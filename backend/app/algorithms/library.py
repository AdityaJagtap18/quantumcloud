"""Prebuilt quantum algorithms, each genuinely constructed as a Qiskit
circuit (then exported to the project's JSON circuit format) rather than
hand-written output tables. Running one through the normal execution
engine is how its "expected output" gets validated.
"""
from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit


_GATE_NAME_MAP = {
    "id": "id", "x": "x", "y": "y", "z": "z", "h": "h", "s": "s", "t": "t",
    "rx": "rx", "ry": "ry", "rz": "rz", "cx": "cx", "cz": "cz", "swap": "swap", "crx": "crx",
}


def _flatten_instructions(qc: QuantumCircuit, outer_qubits: list, outer_clbits: list, condition: dict | None):
    """Yield JSON-schema operation dicts for `qc`'s instructions, mapping its
    local qubit/clbit indices through to the outer (top-level) circuit's
    indices via `outer_qubits`/`outer_clbits`, and tagging every emitted
    gate with `condition` (used when flattening an if_test body)."""
    for instr in qc.data:
        name = instr.operation.name
        local_qubit_idx = [qc.find_bit(q).index for q in instr.qubits]
        local_clbit_idx = [qc.find_bit(c).index for c in instr.clbits]
        qubit_indices = [outer_qubits[i] for i in local_qubit_idx]
        clbit_indices = [outer_clbits[i] for i in local_clbit_idx]

        if name == "measure":
            yield {"gate": "measure", "qubits": qubit_indices, "clbits": clbit_indices}
        elif name == "if_else":
            true_body = instr.operation.blocks[0]
            cond_bits, cond_value = instr.operation.condition
            outer_cond_clbit = outer_clbits[qc.find_bit(cond_bits).index]
            nested_condition = {"clbit": outer_cond_clbit, "equals": int(cond_value)}
            yield from _flatten_instructions(true_body, qubit_indices, clbit_indices, nested_condition)
        elif name in _GATE_NAME_MAP:
            params = [float(p) for p in instr.operation.params]
            op = {"gate": _GATE_NAME_MAP[name], "qubits": qubit_indices}
            if params:
                op["params"] = params
            if condition is not None:
                op["condition"] = condition
            yield op
        else:
            raise ValueError(f"Algorithm circuit uses gate '{name}' with no JSON mapping")


def _to_json(qc: QuantumCircuit) -> dict[str, Any]:
    """Convert a Qiskit circuit back into this project's JSON circuit format."""
    all_qubits = list(range(qc.num_qubits))
    all_clbits = list(range(qc.num_clbits))
    operations = list(_flatten_instructions(qc, all_qubits, all_clbits, None))
    return {"num_qubits": qc.num_qubits, "num_clbits": qc.num_clbits, "operations": operations}


def bell_state() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc


def ghz_state(n: int = 3) -> QuantumCircuit:
    qc = QuantumCircuit(n, n)
    qc.h(0)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    qc.measure(range(n), range(n))
    return qc


def quantum_teleportation() -> QuantumCircuit:
    """Teleport qubit 0's state (prepared as |+>) onto qubit 2 using
    qubit 1 as the entangled resource, with classically-controlled
    corrections applied via a mid-circuit measurement + conditional gates.
    """
    qc = QuantumCircuit(3, 3)
    qc.h(0)  # state to teleport: |+>
    qc.h(1)
    qc.cx(1, 2)  # Bell pair between qubit 1 (Alice) and qubit 2 (Bob)
    qc.cx(0, 1)
    qc.h(0)
    qc.measure(0, 0)
    qc.measure(1, 1)
    with qc.if_test((qc.clbits[1], 1)):
        qc.x(2)
    with qc.if_test((qc.clbits[0], 1)):
        qc.z(2)
    qc.measure(2, 2)
    return qc


def deutsch_jozsa(n: int = 3, balanced: bool = True) -> QuantumCircuit:
    """Deutsch-Jozsa with an n-bit input register + 1 ancilla.
    Oracle: balanced -> CNOT from each input qubit to ancilla;
    constant -> identity (f(x) = 0 for all x)."""
    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))
    if balanced:
        for i in range(n):
            qc.cx(i, n)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def bernstein_vazirani(secret: str = "101") -> QuantumCircuit:
    n = len(secret)
    qc = QuantumCircuit(n + 1, n)
    qc.x(n)
    qc.h(range(n + 1))
    for i, bit in enumerate(reversed(secret)):
        if bit == "1":
            qc.cx(i, n)
    qc.h(range(n))
    qc.measure(range(n), range(n))
    return qc


def grover_2qubit_search(target: str = "11") -> QuantumCircuit:
    """Grover search over 2 qubits (4-item space) for a 2-bit target,
    with exactly one optimal iteration (pi/4 * sqrt(4) ~ 1 iteration)."""
    qc = QuantumCircuit(2, 2)
    qc.h([0, 1])

    def oracle(circuit: QuantumCircuit):
        if target[0] == "0":
            circuit.x(1)
        if target[1] == "0":
            circuit.x(0)
        circuit.cz(0, 1)
        if target[0] == "0":
            circuit.x(1)
        if target[1] == "0":
            circuit.x(0)

    def diffuser(circuit: QuantumCircuit):
        circuit.h([0, 1])
        circuit.x([0, 1])
        circuit.cz(0, 1)
        circuit.x([0, 1])
        circuit.h([0, 1])

    oracle(qc)
    diffuser(qc)
    qc.measure([0, 1], [0, 1])
    return qc


def quantum_fourier_transform(n: int = 3) -> QuantumCircuit:
    import math

    qc = QuantumCircuit(n, n)
    for j in range(n):
        qc.h(j)
        for k in range(j + 1, n):
            qc.crx(math.pi / (2 ** (k - j)), k, j)
    for i in range(n // 2):
        qc.swap(i, n - i - 1)
    qc.measure(range(n), range(n))
    return qc


ALGORITHMS: dict[str, dict[str, Any]] = {
    "bell_state": {
        "name": "Bell State Preparation",
        "description": "Prepares the maximally entangled state (|00> + |11>)/sqrt(2) using H + CNOT.",
        "math_intuition": "H puts qubit 0 into an equal superposition; CNOT entangles qubit 1 with it, "
                           "so measuring either qubit fully determines the other.",
        "builder": bell_state,
        "expected_distribution": {"00": 0.5, "11": 0.5},
    },
    "ghz_state": {
        "name": "GHZ State Preparation",
        "description": "Prepares the n-qubit generalization of the Bell state: (|00..0> + |11..1>)/sqrt(2).",
        "math_intuition": "A chain of CNOTs propagates qubit 0's superposition into a single "
                           "multi-qubit entangled state.",
        "builder": lambda: ghz_state(3),
        "expected_distribution": {"000": 0.5, "111": 0.5},
    },
    "quantum_teleportation": {
        "name": "Quantum Teleportation",
        "description": "Teleports the state of qubit 0 onto qubit 2 using an entangled pair and classical corrections.",
        "math_intuition": "Bell-basis measurement on the sender's qubits collapses the joint state; "
                           "classically communicating the outcome lets the receiver apply the right "
                           "Pauli correction to recover the original state.",
        "builder": quantum_teleportation,
        "expected_distribution": None,  # depends on mid-circuit measurement outcomes; see Noise Studio for fidelity
    },
    "deutsch_jozsa": {
        "name": "Deutsch-Jozsa Algorithm",
        "description": "Determines in one query whether a black-box function is constant or balanced.",
        "math_intuition": "Phase kickback from the oracle interferes constructively on |00...0> only "
                           "if the function is constant.",
        "builder": lambda: deutsch_jozsa(3, balanced=True),
        "expected_distribution": {"111": 1.0},  # any nonzero outcome => balanced, for this balanced oracle
    },
    "bernstein_vazirani": {
        "name": "Bernstein-Vazirani Algorithm",
        "description": "Recovers a hidden n-bit secret string using a single oracle query.",
        "math_intuition": "The oracle phase-kicks the ancilla based on the dot product of input and secret; "
                           "Hadamard interference leaves the secret string as the only measured outcome.",
        "builder": lambda: bernstein_vazirani("101"),
        "expected_distribution": {"101": 1.0},
    },
    "grover_search": {
        "name": "Grover Search (2-qubit)",
        "description": "Amplifies the amplitude of a marked 2-qubit item using one Grover iteration.",
        "math_intuition": "The oracle flips the marked state's phase; the diffuser reflects amplitudes "
                           "about the mean, concentrating probability on the marked item.",
        "builder": lambda: grover_2qubit_search("11"),
        "expected_distribution": {"11": 1.0},  # exact for 2 qubits / 1 iteration
    },
    "qft": {
        "name": "Quantum Fourier Transform",
        "description": "Applies the quantum analogue of the discrete Fourier transform to the input register.",
        "math_intuition": "Controlled phase rotations encode frequency information into relative phases "
                           "across qubits, following the same structure as the classical FFT.",
        "builder": lambda: quantum_fourier_transform(3),
        "expected_distribution": None,  # depends on input state; starting from |000> gives uniform superposition
    },
}


def get_algorithm_circuit_json(algorithm_id: str) -> dict[str, Any]:
    if algorithm_id not in ALGORITHMS:
        raise KeyError(f"Unknown algorithm '{algorithm_id}'. Options: {list(ALGORITHMS)}")
    qc = ALGORITHMS[algorithm_id]["builder"]()
    return _to_json(qc)


def list_algorithms() -> list[dict[str, Any]]:
    return [
        {
            "id": key,
            "name": value["name"],
            "description": value["description"],
            "math_intuition": value["math_intuition"],
            "expected_distribution": value["expected_distribution"],
        }
        for key, value in ALGORITHMS.items()
    ]
