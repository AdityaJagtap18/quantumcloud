"""Noise Experimentation Studio: run the same circuit at several noise
levels, synchronously (so results are available immediately for the
comparison charts), and record fidelity/observable-error metrics.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Experiment, ExperimentRun, User
from app.quantum.circuit_builder import CircuitValidationError, build_circuit, validate_circuit_json
from app.quantum.engine import execute_circuit
from app.quantum.noise_models import build_noise_model


def _total_variation_distance(p: dict[str, float], q: dict[str, float]) -> float:
    """0 = identical distributions, 1 = disjoint supports. Used as the
    'observable error' between a noisy and an ideal measurement
    distribution when no reference statevector is supplied."""
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def run_noise_sweep(
    db: Session,
    user: User,
    experiment_name: str,
    circuit_config: dict,
    shots: int,
    noise_levels: list[float],
) -> Experiment:
    try:
        validate_circuit_json(circuit_config)
    except CircuitValidationError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    circuit = build_circuit(circuit_config)
    if not circuit.clbits:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Noise sweep circuits must include measurements")

    experiment = Experiment(
        user_id=user.id,
        experiment_name=experiment_name,
        experiment_config={"circuit": circuit_config, "shots": shots, "noise_levels": noise_levels},
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    # Baseline: ideal (noiseless) distribution, used as the reference for
    # observable error at every noise level.
    ideal_result = execute_circuit(circuit, "ideal_qasm", shots=max(shots, 4000))
    ideal_distribution = ideal_result.probabilities

    for level in noise_levels:
        noise_config = {
            "single_qubit_gate_error": level,
            "two_qubit_gate_error": min(level * 2, 1.0),
            "measurement_error": level,
            "error_types": ["depolarizing", "readout"],
        }
        start = time.perf_counter()
        result = execute_circuit(circuit, "custom_noise", shots=shots, noise_config=noise_config)
        elapsed = time.perf_counter() - start

        observable_error = _total_variation_distance(ideal_distribution, result.probabilities)
        fidelity_proxy = 1.0 - observable_error  # classical-fidelity proxy from shot statistics

        run = ExperimentRun(
            experiment_id=experiment.id,
            noise_level=level,
            job_id=None,
            metrics={
                "measurement_counts": result.measurement_counts,
                "probabilities": result.probabilities,
                "observable_error": observable_error,
                "fidelity_proxy": fidelity_proxy,
                "execution_time_seconds": elapsed,
            },
        )
        db.add(run)

    db.commit()
    db.refresh(experiment)
    return experiment
