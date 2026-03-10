import itertools
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

TeamId = int
DealId = int
RoundId = int
TableNumber = int

# Valid positions (bridge): used for both dealer and declarer
DECLARERS = ("N", "E", "S", "W")
# Valid vulnerability (bridge: None, N-S, E-W, Both)
VULNERABILITIES = ("None", "N-S", "E-W", "Both")

# Standard board cycle: (dealer, vulnerability) per position.
# For 1–16 boxes we use the first N entries; tournaments with number_of_boxes N
# derive dealer/vuln from deal_dealer_vulnerability(box, number_of_boxes).
BOARD_DEAL_CYCLE: Tuple[Tuple[str, str], ...] = (
    ("N", "None"),   # 1
    ("E", "N-S"),    # 2
    ("S", "E-W"),    # 3
    ("W", "Both"),   # 4
    ("N", "N-S"),    # 5
    ("E", "E-W"),    # 6
    ("S", "Both"),   # 7
    ("W", "None"),   # 8
    ("N", "E-W"),    # 9
    ("E", "Both"),   # 10
    ("S", "None"),   # 11
    ("W", "N-S"),    # 12
    ("N", "N-S"),   # 13
    ("E", "E-W"),   # 14
    ("S", "Both"),   # 15
    ("W", "None"),   # 16
)
MAX_CYCLE_LEN = len(BOARD_DEAL_CYCLE)


@dataclass
class TeamMember:
    """A single member of a team."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("TeamMember.name must be a string")
        if not self.name.strip():
            raise ValueError("TeamMember.name must be non-empty")


@dataclass
class Team:
    """Represents a single team in the tournament."""

    id: TeamId
    name: str
    member1: TeamMember
    member2: TeamMember

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("Team.name must be a string")
        if not self.name.strip():
            raise ValueError("Team.name must be non-empty")
        if not isinstance(self.member1, TeamMember):
            raise TypeError("Team.member1 must be a TeamMember")
        if not isinstance(self.member2, TeamMember):
            raise TypeError("Team.member2 must be a TeamMember")


@dataclass
class Deal:
    """
    A single deal (board) in a round. Stores only identity and physical box.
    Dealer and vulnerability are derived from box and tournament number_of_boxes
    via deal_dealer_vulnerability(box, number_of_boxes), using a short cycle
    (first N entries of the standard pattern when using N boxes).
    """

    id: DealId
    box: int  # Physical box 1..number_of_boxes

    def __post_init__(self) -> None:
        if not isinstance(self.box, int) or self.box < 1:
            raise ValueError("Deal.box must be an integer >= 1")


def deal_dealer_vulnerability(box: int, number_of_boxes: int) -> Tuple[str, str]:
    """
    Dealer and vulnerability for a deal from its box and tournament box count.
    Uses a cycle of length min(16, number_of_boxes): e.g. 4 boxes use the
    first 4 entries of the standard pattern; 16 boxes use all 16.
    """
    if number_of_boxes < 1:
        raise ValueError("number_of_boxes must be >= 1")
    cycle_len = min(MAX_CYCLE_LEN, number_of_boxes)
    idx = (box - 1) % cycle_len
    return BOARD_DEAL_CYCLE[idx]


def box_for_deal(deal_number: int, number_of_boxes: int) -> int:
    """
    Physical box index (1..number_of_boxes) for a deal by its global board number.
    Boxes cycle 1, 2, …, number_of_boxes, 1, 2, …
    """
    if number_of_boxes < 1:
        raise ValueError("number_of_boxes must be >= 1")
    return ((deal_number - 1) % number_of_boxes) + 1


def deal_from_board_number(board_id: int, number_of_boxes: int = 1) -> Deal:
    """
    Create a Deal for a given global board number. Box is cycled 1..number_of_boxes.
    Dealer/vulnerability are derived from box via deal_dealer_vulnerability when needed.
    """
    if board_id < 1:
        raise ValueError("board_id must be >= 1")
    number_of_boxes = max(1, number_of_boxes)
    box = box_for_deal(board_id, number_of_boxes)
    return Deal(id=board_id, box=box)


def standard_16_board_deal_sequence(
    start_id: int = 1, number_of_boxes: int = 1
) -> Iterator[Deal]:
    """
    Infinite generator of deals. Box cycles 1..number_of_boxes; dealer/vuln
    are derived from box and number_of_boxes when needed.
    """
    if start_id < 1:
        raise ValueError("start_id must be >= 1")
    number_of_boxes = max(1, number_of_boxes)
    for board_id in itertools.count(start_id):
        yield deal_from_board_number(board_id, number_of_boxes)


@dataclass
class TableAssignment:
    """
    Assignment of teams to a physical table for a specific round.

    Each table has one team sitting North‑South and one sitting East‑West.
    """

    table_number: TableNumber
    ns_team_id: TeamId
    ew_team_id: TeamId


@dataclass
class Result:
    """
    Result of a single deal at a single table in a specific round.
    """

    round_id: RoundId
    table_number: TableNumber
    deal_id: DealId
    ns_score: int
    ew_score: int
    contract: str = ""
    declarer: str = ""  # N, S, E, or W (who declared the contract)
    opening_lead: str = ""
    tricks_taken: Optional[int] = None


@dataclass
class Round:
    """
    All information for a single round:
    - table assignments (who sits NS / EW at each table)
    - deals assigned to this round
    - results for every (table, deal) combination
    """

    id: RoundId
    round_number: int
    tables: List[TableAssignment]
    deals: List[Deal]
    results_by_table_deal: Dict[Tuple[TableNumber, DealId], Result]
