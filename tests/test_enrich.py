from __future__ import annotations

from etl.enrich import detect_conflict, merge_field


def test_merge_field_rellena_cuando_actual_desconocido() -> None:
    value, changed = merge_field(
        current_value="desconocido",
        candidate_value="O'Reilly",
        candidate_confidence=0.92,
        min_confidence=0.75,
    )
    assert changed is True
    assert value == "O'Reilly"


def test_merge_field_no_rellena_si_confianza_baja() -> None:
    value, changed = merge_field(
        current_value="desconocido",
        candidate_value="O'Reilly",
        candidate_confidence=0.60,
        min_confidence=0.75,
    )
    assert changed is False
    assert value == "desconocido"


def test_merge_field_no_pisa_valor_existente() -> None:
    value, changed = merge_field(
        current_value="Manning",
        candidate_value="O'Reilly",
        candidate_confidence=0.95,
        min_confidence=0.75,
    )
    assert changed is False
    assert value == "Manning"


def test_detect_conflict_con_confianza_alta() -> None:
    assert detect_conflict("Manning", "O'Reilly", confidence=0.90) is True


def test_detect_conflict_no_marca_si_mismo_valor() -> None:
    assert detect_conflict("Manning", "Manning", confidence=0.99) is False
