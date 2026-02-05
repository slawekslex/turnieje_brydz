"""
Validation for deal result fields (contract, declarer, opening_lead, tricks_taken).
"""

from bridge.models.contract import validate_contract_string
from bridge.models.round_models import DECLARERS


def validate_result_fields(
    contract: str, declarer: str, opening_lead: str, tricks_taken
) -> list[dict]:
    """Validate result field values. Returns list of { 'field': str, 'message': str } (empty if valid)."""
    errors = []
    contract = (contract or "").strip()
    if contract and not validate_contract_string(contract):
        errors.append({
            "field": "contract",
            "message": "Kontrakt: poziom 1–7, kolor C/D/H/S/NT, opcjonalnie x lub xx (np. 3NT, 4Sx).",
        })
    declarer = (declarer or "").strip().upper()
    if declarer and declarer not in DECLARERS:
        errors.append({"field": "declarer", "message": "Rozgrywający: N, S, E lub W."})
    if tricks_taken is not None and (
        not isinstance(tricks_taken, int) or tricks_taken < 0 or tricks_taken > 13
    ):
        errors.append({"field": "tricks_taken", "message": "Wziątki: 0–13."})
    return errors


def validate_result_complete(
    contract: str, declarer: str, opening_lead: str, tricks_taken
) -> list[dict]:
    """Require all fields to be filled. Returns list of { 'field', 'message' } for empty fields."""
    errors = []
    if not (contract or "").strip():
        errors.append({"field": "contract", "message": "Wypełnij pole."})
    if not (declarer or "").strip().upper():
        errors.append({"field": "declarer", "message": "Wypełnij pole."})
    if not (opening_lead or "").strip():
        errors.append({"field": "opening_lead", "message": "Wypełnij pole."})
    if tricks_taken is None or (
        isinstance(tricks_taken, str) and tricks_taken.strip() == ""
    ):
        errors.append({"field": "tricks_taken", "message": "Wypełnij pole."})
    return errors
