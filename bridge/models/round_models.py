import itertools
from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple

TeamId = int
DealId = int
RoundId = int
TableNumber = int

# Valid declarer positions (bridge)
DECLARERS = ("N", "E", "S", "W")
# Valid vulnerability (bridge: None, N-S, E-W, Both)
VULNERABILITIES = ("None", "N-S", "E-W", "Both")


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
    """Represents a single deal (board) in a round."""

    id: DealId
    number: int
    declarer: str
    vulnerability: str

    def __post_init__(self) -> None:
        if not isinstance(self.number, int):
            raise TypeError("Deal.number must be an integer")
        if self.number < 1:
            raise ValueError("Deal.number must be >= 1")
        if not isinstance(self.declarer, str):
            raise TypeError("Deal.declarer must be a string")
        if self.declarer not in DECLARERS:
            raise ValueError(
                f"Deal.declarer must be one of {DECLARERS}, got {self.declarer!r}"
            )
        if not isinstance(self.vulnerability, str):
            raise TypeError("Deal.vulnerability must be a string")
        if self.vulnerability not in VULNERABILITIES:
            raise ValueError(
                f"Deal.vulnerability must be one of {VULNERABILITIES}, "
                f"got {self.vulnerability!r}"
            )


def deal_from_board_number(board_id: int) -> Deal:
    """
    Create a valid Deal for a given board number with standard bridge
    dealer and vulnerability cycling (board 1 = N/None, 2 = E/N-S, etc.).
    """
    return Deal(
        id=board_id,
        number=board_id,
        declarer=DECLARERS[(board_id - 1) % 4],
        vulnerability=VULNERABILITIES[(board_id - 1) % 4],
    )


def standard_16_board_deal_sequence(start_id: int = 1) -> Iterator[Deal]:
    """
    Infinite generator of deals using the standard 16-board (4-box) setup:
    dealer and vulnerability rotate every 4 boards (N/None, E/N-S, S/E-W, W/Both).
    Boards 1–16 form one standard set; the same rotation repeats for 17–32, etc.

    Args:
        start_id: First board number to yield (must be >= 1).
    """
    if start_id < 1:
        raise ValueError("start_id must be >= 1")
    for board_id in itertools.count(start_id):
        yield deal_from_board_number(board_id)


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
