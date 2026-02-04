"""
Bridge contract representation and validation.

Contract format: level (1-7) + suit (C, D, H, S, NT) + optional modifier (x = doubled, xx = redoubled).
Examples: 1C, 3NT, 4Sx, 6Hxx.
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# Valid contract levels (tricks to be made above book)
CONTRACT_LEVELS: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
# Suits: Clubs, Diamonds, Hearts, Spades, No Trump
CONTRACT_SUITS: Tuple[str, ...] = ("C", "D", "H", "S", "NT")
# Modifier: none, doubled, redoubled
CONTRACT_MODIFIERS: Tuple[str, ...] = ("", "x", "xx")

# Regex: 1-7, then C|D|H|S|NT, then optional x or xx (capture groups for level, suit, modifier)
CONTRACT_PATTERN = re.compile(
    r"^\s*([1-7])\s*(C|D|H|S|NT)\s*(|x|xx)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Contract:
    """A bridge contract: level, suit, and optional double/redouble."""

    level: int
    suit: str
    modifier: str  # "", "x", or "xx"

    def __post_init__(self) -> None:
        if self.level not in CONTRACT_LEVELS:
            raise ValueError(f"Level must be 1-7, got {self.level}")
        if self.suit.upper() not in CONTRACT_SUITS:
            raise ValueError(f"Suit must be one of {CONTRACT_SUITS}, got {self.suit!r}")
        if self.modifier not in CONTRACT_MODIFIERS:
            raise ValueError(f"Modifier must be '', 'x', or 'xx', got {self.modifier!r}")


def parse_contract(s: str) -> Optional[Contract]:
    """
    Parse a contract string into a Contract, or return None if invalid/empty.
    Accepts e.g. "3NT", "4Sx", "6Hxx". Case-insensitive for suit.
    """
    if not s or not s.strip():
        return None
    m = CONTRACT_PATTERN.match(s.strip())
    if not m:
        return None
    level = int(m.group(1))
    suit = m.group(2).upper()
    modifier = m.group(3).lower()
    return Contract(level=level, suit=suit, modifier=modifier)


def format_contract(c: Contract) -> str:
    """Format a Contract to canonical string (e.g. 3NT, 4Sx)."""
    return f"{c.level}{c.suit}{c.modifier}"


def validate_contract_string(s: str) -> bool:
    """Return True if the string is a valid contract (or empty)."""
    if not s or not s.strip():
        return True
    return parse_contract(s) is not None
