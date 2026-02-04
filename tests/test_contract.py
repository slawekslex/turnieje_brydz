"""Unit tests for bridge contract parsing, formatting, and validation."""

import pytest

from bridge.models.contract import (
    CONTRACT_LEVELS,
    CONTRACT_MODIFIERS,
    CONTRACT_PATTERN,
    CONTRACT_SUITS,
    Contract,
    format_contract,
    parse_contract,
    validate_contract_string,
)


class ContractConstantsTests:
    def test_levels(self):
        assert CONTRACT_LEVELS == (1, 2, 3, 4, 5, 6, 7)

    def test_suits(self):
        assert CONTRACT_SUITS == ("C", "D", "H", "S", "NT")

    def test_modifiers(self):
        assert CONTRACT_MODIFIERS == ("", "x", "xx")

    def test_pattern_matches_valid(self):
        assert CONTRACT_PATTERN.match("1C")
        assert CONTRACT_PATTERN.match("3NT")
        assert CONTRACT_PATTERN.match("4Sx")
        assert CONTRACT_PATTERN.match("6Hxx")
        assert CONTRACT_PATTERN.match("  2D  ")
        assert CONTRACT_PATTERN.match("7nt")

    def test_pattern_rejects_invalid(self):
        assert CONTRACT_PATTERN.match("0C") is None
        assert CONTRACT_PATTERN.match("8S") is None
        assert CONTRACT_PATTERN.match("3X") is None
        assert CONTRACT_PATTERN.match("3") is None
        assert CONTRACT_PATTERN.match("NT") is None
        # 3NTx is valid (3 no trump doubled)


class ContractDataclassTests:
    def test_valid_contract(self):
        c = Contract(level=3, suit="NT", modifier="")
        assert c.level == 3 and c.suit == "NT" and c.modifier == ""

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Level must be 1-7"):
            Contract(level=0, suit="C", modifier="")
        with pytest.raises(ValueError, match="Level must be 1-7"):
            Contract(level=8, suit="C", modifier="")

    def test_invalid_suit_raises(self):
        with pytest.raises(ValueError, match="Suit must be"):
            Contract(level=1, suit="X", modifier="")

    def test_invalid_modifier_raises(self):
        with pytest.raises(ValueError, match="Modifier"):
            Contract(level=1, suit="C", modifier="xxx")


class ParseContractTests:
    def test_valid_strings(self):
        assert parse_contract("1C") == Contract(level=1, suit="C", modifier="")
        assert parse_contract("3NT") == Contract(level=3, suit="NT", modifier="")
        assert parse_contract("4Sx") == Contract(level=4, suit="S", modifier="x")
        assert parse_contract("6Hxx") == Contract(level=6, suit="H", modifier="xx")
        assert parse_contract("  2D  ") == Contract(level=2, suit="D", modifier="")
        assert parse_contract("7nt") == Contract(level=7, suit="NT", modifier="")
        assert parse_contract("3NTx") == Contract(level=3, suit="NT", modifier="x")

    def test_empty_returns_none(self):
        assert parse_contract("") is None
        assert parse_contract("   ") is None

    def test_invalid_returns_none(self):
        assert parse_contract("0C") is None
        assert parse_contract("8S") is None
        assert parse_contract("3X") is None
        assert parse_contract("abc") is None


class FormatContractTests:
    def test_format(self):
        assert format_contract(Contract(1, "C", "")) == "1C"
        assert format_contract(Contract(3, "NT", "")) == "3NT"
        assert format_contract(Contract(4, "S", "x")) == "4Sx"
        assert format_contract(Contract(6, "H", "xx")) == "6Hxx"


class ValidateContractStringTests:
    def test_empty_valid(self):
        assert validate_contract_string("") is True
        assert validate_contract_string("  ") is True

    def test_valid_contracts(self):
        assert validate_contract_string("1C") is True
        assert validate_contract_string("3NT") is True
        assert validate_contract_string("4Sx") is True
        assert validate_contract_string("6Hxx") is True
        assert validate_contract_string("3NTx") is True

    def test_invalid_contracts(self):
        assert validate_contract_string("0C") is False
        assert validate_contract_string("8S") is False
        assert validate_contract_string("3X") is False
        assert validate_contract_string("x") is False
