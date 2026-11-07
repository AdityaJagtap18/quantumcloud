"""Circuit resource analysis: logical (pre-transpile) and physical
(post-transpile) gate counts, depth, and transpilation overhead against
a configurable hardware coupling map.
"""
from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap

# A few illustrative hardware topologies. Real backends expose their own
# coupling maps; these are representative shapes for demonstration.
COUPLING_MAPS: dict[str, list[list[int]] | None] = {
    "fully_connected": None,  # no constraint
    "linear": None,  # built dynamically based on num_qubits
    "ring": None,  # built dynamically based on num_qubits
    "heavy_hex_like": [[0, 1], [1, 2], [2, 3], [1, 4], [4, 5], [5, 6], [4, 7]],
}


def _build_coupling_map(topology: str, num_qubits: int) -> CouplingMap | None:
    if topology == "fully_connected":
        return None
    if topology == "linear":
        edges = [[i, i + 1] for i in range(num_qubits - 1)]
        return CouplingMap(edges) if edges else None
    if topology == "ring":
        edges = [[i, (i + 1) % num_qubits] for i in range(num_qubits)]
        return CouplingMap(edges) if num_qubits > 1 else None
    if topology in COUPLING_MAPS and COUPLING_MAPS[topology] is not None:
        return CouplingMap(COUPLING_MAPS[topology])
    raise ValueError(f"Unknown topology '{topology}'. Options: {list(COUPLING_MAPS)}")


def analyze_logical_circuit(circuit: QuantumCircuit) -> dict[str, Any]:
    """Resource counts BEFORE transpilation — the circuit as the user wrote it."""
    ops = circuit.count_ops()
    single_qubit = sum(count for gate, count in ops.items() if gate not in ("measure", "barrier") and _gate_arity(circuit, gate) == 1)
    two_qubit = sum(count for gate, count in ops.items() if gate not in ("measure", "barrier") and _gate_arity(circuit, gate) == 2)

    return {
        "num_qubits": circuit.num_qubits,
        "num_clbits": circuit.num_clbits,
        "total_gate_count": sum(count for gate, count in ops.items() if gate != "measure"),
        "single_qubit_gate_count": single_qubit,
        "two_qubit_gate_count": two_qubit,
        "depth": circuit.depth(),
        "num_measurements": ops.get("measure", 0),
        "width": circuit.width(),
        "gate_distribution": dict(ops),
    }


def _gate_arity(circuit: QuantumCircuit, gate_name: str) -> int:
    for instr in circuit.data:
        if instr.operation.name == gate_name:
            return len(instr.qubits)
    return 0


def analyze_transpiled_circuit(
    circuit: QuantumCircuit, topology: str = "fully_connected", optimization_level: int = 1
) -> dict[str, Any]:
    """Resource counts AFTER transpilation for a given hardware topology."""
    coupling_map = _build_coupling_map(topology, circuit.num_qubits)

    import time

    start = time.perf_counter()
    transpiled = transpile(
        circuit,
        coupling_map=coupling_map,
        optimization_level=optimization_level,
        basis_gates=["id", "rz", "sx", "x", "cx"] if coupling_map is not None else None,
    )
    transpile_time = time.perf_counter() - start

    ops = transpiled.count_ops()
    swap_count = ops.get("swap", 0)

    logical = analyze_logical_circuit(circuit)
    total_gates_after = sum(count for gate, count in ops.items() if gate != "measure")

    return {
        "topology": topology,
        "transpiled_depth": transpiled.depth(),
        "transpiled_gate_count": total_gates_after,
        "native_gate_distribution": dict(ops),
        "swap_gate_overhead": swap_count,
        "transpile_time_seconds": transpile_time,
        "resource_overhead_ratio": (
            total_gates_after / logical["total_gate_count"] if logical["total_gate_count"] > 0 else None
        ),
        "depth_overhead_ratio": (
            transpiled.depth() / logical["depth"] if logical["depth"] > 0 else None
        ),
    }


def full_resource_report(circuit: QuantumCircuit, topology: str = "fully_connected") -> dict[str, Any]:
    return {
        "logical": analyze_logical_circuit(circuit),
        "transpiled": analyze_transpiled_circuit(circuit, topology=topology),
    }
