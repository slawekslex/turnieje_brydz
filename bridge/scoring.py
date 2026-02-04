"""
Standard duplicate bridge scoring.

Computes NS/EW score from contract, declarer, tricks taken, and vulnerability.
Also provides IMP conversion and deal-level IMP scoring (datum-based).
"""

from typing import List, Optional, Tuple

# Standard IMP table: (upper_bound_inclusive, IMP). Absolute point difference -> IMP.
# Ranges: 0-10->0, 20-40->1, 50-80->2, ... (WBF/standard duplicate bridge).
_IMP_TABLE: List[Tuple[int, int]] = [
    (10, 0),
    (40, 1),
    (80, 2),
    (120, 3),
    (160, 4),
    (210, 5),
    (260, 6),
    (310, 7),
    (360, 8),
    (420, 9),
    (490, 10),
    (590, 11),
    (740, 12),
    (890, 13),
    (1090, 14),
    (1290, 15),
    (1490, 16),
    (1740, 17),
    (1990, 18),
    (2240, 19),
    (2490, 20),
    (2990, 21),
    (3490, 22),
    (3990, 23),
]

from bridge.models.contract import Contract, parse_contract


def _contract_trick_value(contract: Contract) -> int:
    """Trick points for one trick in the contract suit (before doubling)."""
    if contract.suit == "NT":
        return 30  # first trick is 40, subsequent 30; we use 30 for per-trick calc
    if contract.suit in ("H", "S"):
        return 30
    return 20  # C, D


def _contract_first_trick_value(contract: Contract) -> int:
    """Points for the first trick in NT (40); otherwise same as per-trick."""
    if contract.suit == "NT":
        return 40
    return _contract_trick_value(contract)


def _contract_points(contract: Contract) -> int:
    """Raw trick points for the bid (level) before doubling, e.g. 3NT=100, 4S=120."""
    first = _contract_first_trick_value(contract)
    rest = _contract_trick_value(contract) * (contract.level - 1)
    return first + rest


def _is_declarer_vulnerable(declarer: str, vulnerability: str) -> bool:
    """True if the declaring side is vulnerable."""
    declarer = (declarer or "").strip().upper()
    vul = (vulnerability or "").strip()
    if vul == "None":
        return False
    if vul == "Both":
        return True
    if vul == "N-S":
        return declarer in ("N", "S")
    if vul == "E-W":
        return declarer in ("E", "W")
    return False


def _declarer_side_ns(declarer: str) -> bool:
    """True if declarer is N or S (NS pair is declaring side)."""
    return (declarer or "").strip().upper() in ("N", "S")


def compute_score(
    contract_str: str,
    declarer: str,
    tricks_taken: int,
    vulnerability: str,
) -> Optional[Tuple[int, int]]:
    """
    Compute NS and EW score using standard duplicate bridge scoring.

    Args:
        contract_str: e.g. "3NT", "4Sx"
        declarer: N, S, E, or W
        tricks_taken: 0-13
        vulnerability: "None", "N-S", "E-W", "Both"

    Returns:
        (ns_score, ew_score) or None if contract invalid. Score is from NS perspective;
        typically one side positive and the other negative (zero-sum).
    """
    contract = parse_contract(contract_str or "")
    if not contract or not declarer or declarer.strip().upper() not in ("N", "S", "E", "W"):
        return None
    try:
        tricks_taken = int(tricks_taken)
    except (TypeError, ValueError):
        return None
    if not (0 <= tricks_taken <= 13):
        return None

    vul = _is_declarer_vulnerable(declarer, vulnerability)
    contract_tricks = contract.level + 6
    mult = 2 if contract.modifier == "x" else 4 if contract.modifier == "xx" else 1
    trick_val = _contract_trick_value(contract)
    first_trick_val = _contract_first_trick_value(contract)

    if tricks_taken >= contract_tricks:
        # Made contract
        contract_pts = _contract_points(contract) * mult
        raw = contract_pts
        # Overtricks
        overtricks = tricks_taken - contract_tricks
        if contract.modifier == "x":
            raw += overtricks * (200 if vul else 100)
        elif contract.modifier == "xx":
            raw += overtricks * (400 if vul else 200)
        else:
            raw += overtricks * trick_val
        # Bonuses (game = 100+ contract points)
        if contract_pts >= 100:
            raw += 500 if vul else 300
        else:
            raw += 50  # part score
        if contract.modifier == "x":
            raw += 50
        elif contract.modifier == "xx":
            raw += 100
        if contract.level == 6:
            raw += 750 if vul else 500
        elif contract.level == 7:
            raw += 1500 if vul else 1000
    else:
        # Undertricks: defenders get positive points; declaring side gets negative.
        # Scale per Richard Pavlicek / standard duplicate: http://www.rpbridge.net/2y67.htm
        undertricks = contract_tricks - tricks_taken
        if contract.modifier == "":
            defender_pts = undertricks * (100 if vul else 50)
        elif contract.modifier == "x":
            if vul:
                # Vul X: 200, 300, 300, 300, ...
                defender_pts = (200 + 300 * (undertricks - 1)) if undertricks >= 1 else 0
            else:
                # NV X: 100, 200, 200, 300, 300, 300, ... (down 3 = 500, down 4 = 800)
                if undertricks <= 0:
                    defender_pts = 0
                elif undertricks == 1:
                    defender_pts = 100
                elif undertricks == 2:
                    defender_pts = 300
                else:
                    defender_pts = 500 + 300 * (undertricks - 3)
        else:  # xx
            if vul:
                # Vul XX: 400, 600, 600, 600, ...
                defender_pts = (400 + 600 * (undertricks - 1)) if undertricks >= 1 else 0
            else:
                # NV XX: 200, 400, 400, 600, 600, 600, ... (down 3 = 1000, down 4 = 1600)
                if undertricks <= 0:
                    defender_pts = 0
                elif undertricks == 1:
                    defender_pts = 200
                elif undertricks == 2:
                    defender_pts = 600
                else:
                    defender_pts = 1000 + 600 * (undertricks - 3)
        raw = -defender_pts

    # Raw is the score for the declaring side (positive if made, negative if failed)
    if _declarer_side_ns(declarer):
        ns_score = raw
        ew_score = -raw
    else:
        ns_score = -raw
        ew_score = raw

    return (ns_score, ew_score)


def points_to_imp(point_difference: int) -> int:
    """
    Convert a point difference (NS score minus datum) to IMP using the standard table.

    The argument is typically the raw difference; the function uses its absolute value
    to look up IMP, so the sign of point_difference does not affect the IMP magnitude.
    Caller should apply sign for NS/EW (e.g. NS gets +IMP when above datum, EW gets -IMP).

    Args:
        point_difference: Difference in points (e.g. ns_score - datum). Can be negative.

    Returns:
        Non-negative IMP value (0-24) for the absolute point difference.
    """
    d = abs(point_difference)
    for bound, imp in _IMP_TABLE:
        if d <= bound:
            return imp
    return 24


def calculate_deal_imp_scores(ns_scores: List[int]) -> List[Tuple[int, int]]:
    """
    Calculate final IMP scores for a deal across multiple tables (datum-based).

    1) Datum = average of NS scores across all tables, rounded to the nearest 10.
    2) For each table: difference = (NS score on that table) - datum.
    3) Convert absolute difference to IMP via the standard table; NS IMP is
       +IMP if table scored above datum, -IMP if below. EW IMP = -NS IMP.

    Args:
        ns_scores: List of NS scores (one per table) for the same deal.

    Returns:
        List of (ns_imp, ew_imp) for each table, in the same order as ns_scores.
        Empty list if ns_scores is empty.
    """
    if not ns_scores:
        return []
    datum = round(sum(ns_scores) / len(ns_scores), -1)
    result: List[Tuple[int, int]] = []
    for ns in ns_scores:
        diff = ns - datum
        imp_mag = points_to_imp(diff)
        ns_imp = imp_mag if diff >= 0 else -imp_mag
        ew_imp = -ns_imp
        result.append((ns_imp, ew_imp))
    return result
