"""Thin service wrapping circuit validation, resource analysis and
transpilation for the API layer."""
from __future__ import annotations

from app.quantum.analysis import analyze_transpiled_circuit, full_resource_report
from app.quantum.circuit_builder import CircuitValidationError, build_circuit, validate_circuit_json


def validate(circuit_config: dict) -> dict:
    try:
        validate_circuit_json(circuit_config)
        return {"valid": True, "error": None}
    except CircuitValidationError as e:
        return {"valid": False, "error": str(e)}


def analyze(circuit_config: dict, topology: str) -> dict:
    validate_circuit_json(circuit_config)
    circuit = build_circuit(circuit_config)
    return full_resource_report(circuit, topology=topology)


def transpile_report(circuit_config: dict, topology: str, optimization_level: int) -> dict:
    validate_circuit_json(circuit_config)
    circuit = build_circuit(circuit_config)
    return analyze_transpiled_circuit(circuit, topology=topology, optimization_level=optimization_level)
