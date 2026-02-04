"""Unit tests for round_models datatypes and their validations."""
import unittest

from bridge.models.round_models import (
    TeamMember,
    Team,
    Deal,
    deal_from_board_number,
    standard_16_board_deal_sequence,
    DECLARERS,
    VULNERABILITIES,
)


class TeamMemberValidationTests(unittest.TestCase):
    def test_valid_team_member(self) -> None:
        m = TeamMember(name="Alice")
        self.assertEqual(m.name, "Alice")

    def test_team_member_empty_name_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            TeamMember(name="")
        self.assertIn("non-empty", str(ctx.exception))

    def test_team_member_whitespace_only_name_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            TeamMember(name="   \t  ")
        self.assertIn("non-empty", str(ctx.exception))

    def test_team_member_non_string_name_raises(self) -> None:
        with self.assertRaises(TypeError) as ctx:
            TeamMember(name=123)  # type: ignore[arg-type]
        self.assertIn("string", str(ctx.exception))


class TeamValidationTests(unittest.TestCase):
    def _valid_members(self) -> tuple:
        return TeamMember("Alice"), TeamMember("Bob")

    def test_valid_team(self) -> None:
        m1, m2 = self._valid_members()
        t = Team(id=1, name="Team Alpha", member1=m1, member2=m2)
        self.assertEqual(t.name, "Team Alpha")
        self.assertEqual(t.member1.name, "Alice")
        self.assertEqual(t.member2.name, "Bob")

    def test_team_empty_name_raises(self) -> None:
        m1, m2 = self._valid_members()
        with self.assertRaises(ValueError) as ctx:
            Team(id=1, name="", member1=m1, member2=m2)
        self.assertIn("non-empty", str(ctx.exception))

    def test_team_whitespace_only_name_raises(self) -> None:
        m1, m2 = self._valid_members()
        with self.assertRaises(ValueError) as ctx:
            Team(id=1, name="  ", member1=m1, member2=m2)
        self.assertIn("non-empty", str(ctx.exception))

    def test_team_non_string_name_raises(self) -> None:
        m1, m2 = self._valid_members()
        with self.assertRaises(TypeError) as ctx:
            Team(id=1, name=42, member1=m1, member2=m2)  # type: ignore[arg-type]
        self.assertIn("string", str(ctx.exception))

    def test_team_member1_not_team_member_raises(self) -> None:
        m2 = TeamMember("Bob")
        with self.assertRaises(TypeError) as ctx:
            Team(id=1, name="T", member1="Alice", member2=m2)  # type: ignore[arg-type]
        self.assertIn("TeamMember", str(ctx.exception))

    def test_team_member2_not_team_member_raises(self) -> None:
        m1 = TeamMember("Alice")
        with self.assertRaises(TypeError) as ctx:
            Team(id=1, name="T", member1=m1, member2="Bob")  # type: ignore[arg-type]
        self.assertIn("TeamMember", str(ctx.exception))


class DealValidationTests(unittest.TestCase):
    def test_valid_deal(self) -> None:
        d = Deal(id=1, number=1, declarer="N", vulnerability="None")
        self.assertEqual(d.number, 1)
        self.assertEqual(d.declarer, "N")
        self.assertEqual(d.vulnerability, "None")

    def test_deal_number_zero_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=0, number=0, declarer="N", vulnerability="None")
        self.assertIn(">= 1", str(ctx.exception))

    def test_deal_number_negative_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=-1, number=-1, declarer="N", vulnerability="None")
        self.assertIn(">= 1", str(ctx.exception))

    def test_deal_number_non_integer_raises(self) -> None:
        with self.assertRaises(TypeError) as ctx:
            Deal(id=1, number=1.5, declarer="N", vulnerability="None")  # type: ignore[arg-type]
        self.assertIn("integer", str(ctx.exception))

    def test_deal_invalid_declarer_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=1, number=1, declarer="X", vulnerability="None")
        self.assertIn("declarer", str(ctx.exception).lower())
        self.assertIn("N", str(ctx.exception))

    def test_deal_valid_declarers_accepted(self) -> None:
        for declarer in DECLARERS:
            with self.subTest(declarer=declarer):
                d = Deal(id=1, number=1, declarer=declarer, vulnerability="None")
                self.assertEqual(d.declarer, declarer)

    def test_deal_invalid_vulnerability_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=1, number=1, declarer="N", vulnerability="All")
        self.assertIn("vulnerability", str(ctx.exception).lower())

    def test_deal_valid_vulnerabilities_accepted(self) -> None:
        for vul in VULNERABILITIES:
            with self.subTest(vulnerability=vul):
                d = Deal(id=1, number=1, declarer="N", vulnerability=vul)
                self.assertEqual(d.vulnerability, vul)

    def test_deal_declarer_non_string_raises(self) -> None:
        with self.assertRaises(TypeError) as ctx:
            Deal(id=1, number=1, declarer=1, vulnerability="None")  # type: ignore[arg-type]
        self.assertIn("string", str(ctx.exception))

    def test_deal_vulnerability_non_string_raises(self) -> None:
        with self.assertRaises(TypeError) as ctx:
            Deal(id=1, number=1, declarer="N", vulnerability=None)  # type: ignore[arg-type]
        self.assertIn("string", str(ctx.exception))


class DealFromBoardNumberTests(unittest.TestCase):
    def test_deal_from_board_number_cycles_declarer_and_vulnerability(self) -> None:
        d1 = deal_from_board_number(1)
        self.assertEqual(d1.number, 1)
        self.assertEqual(d1.declarer, "N")
        self.assertEqual(d1.vulnerability, "None")

        d2 = deal_from_board_number(2)
        self.assertEqual(d2.declarer, "E")
        self.assertEqual(d2.vulnerability, "N-S")

        d5 = deal_from_board_number(5)
        self.assertEqual(d5.declarer, "N")
        self.assertEqual(d5.vulnerability, "None")

    def test_deal_from_board_number_zero_raises(self) -> None:
        with self.assertRaises(ValueError):
            deal_from_board_number(0)

    def test_deal_from_board_number_negative_raises(self) -> None:
        with self.assertRaises(ValueError):
            deal_from_board_number(-1)


class Standard16BoardDealSequenceTests(unittest.TestCase):
    def test_first_16_boards_follow_standard_rotation(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=1)
        for i in range(16):
            d = next(gen)
            self.assertEqual(d.number, i + 1)
            self.assertEqual(d.declarer, DECLARERS[i % 4])
            self.assertEqual(d.vulnerability, VULNERABILITIES[i % 4])

    def test_start_id_zero_raises(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=0)
        with self.assertRaises(ValueError) as ctx:
            next(gen)
        self.assertIn("start_id", str(ctx.exception))

    def test_custom_start_id(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=17)
        d = next(gen)
        self.assertEqual(d.number, 17)
        self.assertEqual(d.declarer, "N")
        self.assertEqual(d.vulnerability, "None")


if __name__ == "__main__":
    unittest.main()
