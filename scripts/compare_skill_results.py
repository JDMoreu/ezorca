#!/usr/bin/env python3
"""Compare two complete skill evaluations against a fixed rubric."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

Criterion = tuple[str, str]
Trial = tuple[str, str, int]


def read_json(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} debe contener un objeto JSON")
    return value


def entries(record: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    value = record.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, dict) for item in value)
    ):
        raise ValueError(f"{key} debe ser una lista de objetos no vacía")
    return value


def identifier(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} debe ser un identificador de texto")
    return value


def read_rubric(
    record: Mapping[str, Any],
) -> tuple[int, dict[Criterion, bool]]:
    repeats = record.get("repeats")
    if type(repeats) is not int or repeats < 1:
        raise ValueError("repeats debe ser un entero positivo")

    case_ids = set()
    critical_by_criterion = {}
    for case in entries(record, "cases"):
        case_id = identifier(case, "id")
        if case_id in case_ids:
            raise ValueError(f"Caso duplicado: {case_id}")
        case_ids.add(case_id)
        for criterion in entries(case, "criteria"):
            key = (case_id, identifier(criterion, "id"))
            if key in critical_by_criterion:
                raise ValueError(f"Criterio duplicado: {key}")
            critical = criterion.get("critical", False)
            if type(critical) is not bool:
                raise ValueError(f"critical debe ser booleano en {key}")
            critical_by_criterion[key] = critical
    if repeats * len(critical_by_criterion) > 100_000:
        raise ValueError("La rúbrica supera 100000 juicios por variante")
    return repeats, critical_by_criterion


def read_judgments(
    record: Mapping[str, Any],
    expected: set[Trial],
) -> dict[Trial, bool]:
    judgments = {}
    for item in entries(record, "judgments"):
        repetition = item.get("repeat")
        if type(repetition) is not int:
            raise ValueError("repeat debe ser un entero")
        key = (identifier(item, "case"), identifier(item, "criterion"), repetition)
        if key not in expected:
            raise ValueError(f"Juicio fuera de la rúbrica: {key}")
        if key in judgments:
            raise ValueError(f"Juicio duplicado: {key}")
        passed = item.get("passed")
        if type(passed) is not bool:
            raise ValueError(f"passed debe ser booleano en {key}")
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(f"Falta evidencia en {key}")
        judgments[key] = passed
    missing = expected.difference(judgments)
    if missing:
        raise ValueError(f"Faltan {len(missing)} juicios, por ejemplo {min(missing)}")
    return judgments


def pass_k(
    criteria: Mapping[Criterion, bool], judgments: Mapping[Trial, bool], repeats: int
) -> dict[str, Any]:
    """pass@k y pass^k por caso. Una repetición aprueba si cumple los criterios
    críticos del caso (todos los criterios si el caso no tiene ninguno crítico)."""
    cases: dict[str, list[Criterion]] = {}
    for key in criteria:
        cases.setdefault(key[0], []).append(key)
    result = {}
    for case, keys in sorted(cases.items()):
        required = [key for key in keys if criteria[key]] or keys
        runs = [
            all(judgments[(*key, repeat)] for key in required)
            for repeat in range(1, repeats + 1)
        ]
        result[case] = {"pass_at_k": any(runs), "pass_hat_k": all(runs)}
    return {
        "cases": result,
        "total_pass_at_k": sum(item["pass_at_k"] for item in result.values()),
        "total_pass_hat_k": sum(item["pass_hat_k"] for item in result.values()),
    }


def compare(
    rubric: Mapping[str, Any], original: Mapping[str, Any], proposed: Mapping[str, Any]
) -> dict[str, Any]:
    repeats, criteria = read_rubric(rubric)
    repetitions = range(1, repeats + 1)
    expected = {(case, criterion, repeat) for case, criterion in criteria for repeat in repetitions}
    baseline = read_judgments(original, expected)
    candidate = read_judgments(proposed, expected)
    baseline_passes = sum(baseline.values())
    candidate_passes = sum(candidate.values())
    regressions = []
    critical_failures = []
    for (case, criterion), critical in sorted(criteria.items()):
        keys = [(case, criterion, repeat) for repeat in repetitions]
        old_passes = sum(baseline[key] for key in keys)
        new_passes = sum(candidate[key] for key in keys)
        if new_passes < old_passes:
            regressions.append(
                {
                    "case": case,
                    "criterion": criterion,
                    "baseline_passes": old_passes,
                    "candidate_passes": new_passes,
                }
            )
        if critical:
            critical_failures.extend(
                {"case": case, "criterion": criterion, "repeat": key[2]}
                for key in keys
                if not candidate[key]
            )
    baseline_k = pass_k(criteria, baseline, repeats)
    candidate_k = pass_k(criteria, candidate, repeats)
    reliability_regression = candidate_k["total_pass_hat_k"] < baseline_k["total_pass_hat_k"]
    warnings = []
    if repeats == 1:
        warnings.append(
            "Con una sola repetición pass@k y pass^k coinciden; "
            "usa repeats >= 2 para medir confiabilidad"
        )
    return {
        "accepted": candidate_passes > baseline_passes
        and not regressions
        and not critical_failures
        and not reliability_regression,
        "baseline_passes": baseline_passes,
        "candidate_passes": candidate_passes,
        "total_judgments_per_variant": len(expected),
        "regressions": regressions,
        "critical_failures": critical_failures,
        "baseline_pass_k": baseline_k,
        "candidate_pass_k": candidate_k,
        "reliability_regression": reliability_regression,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rubric", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    try:
        result = compare(
            read_json(args.rubric), read_json(args.baseline), read_json(args.candidate)
        )
    except (OSError, ValueError) as error:
        json.dump({"error": str(error)}, sys.stdout, ensure_ascii=True)
        sys.stdout.write("\n")
        return 2
    json.dump(result, sys.stdout, ensure_ascii=True, indent=2)
    sys.stdout.write("\n")
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
