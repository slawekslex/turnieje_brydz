"""Unit tests for round_models datatypes and their validations."""
import unittest

from bridge.models.round_models import (
    BOARD_DEAL_CYCLE,
    DECLARERS,
    VULNERABILITIES,
    Deal,
    Team,
    TeamMember,
    box_for_deal,
    deal_dealer_vulnerability,
    deal_from_board_number,
    standard_16_board_deal_sequence,
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
        d = Deal(id=1, box=1)
        self.assertEqual(d.id, 1)
        self.assertEqual(d.box, 1)

    def test_deal_box_zero_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=1, box=0)
        self.assertIn(">= 1", str(ctx.exception))

    def test_deal_box_negative_raises(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            Deal(id=1, box=-1)
        self.assertIn(">= 1", str(ctx.exception))


class DealFromBoardNumberTests(unittest.TestCase):
    def test_deal_from_board_number_stores_id_and_box(self) -> None:
        d1 = deal_from_board_number(1, number_of_boxes=1)
        self.assertEqual(d1.id, 1)
        self.assertEqual(d1.box, 1)

        d2 = deal_from_board_number(2, number_of_boxes=4)
        self.assertEqual(d2.id, 2)
        self.assertEqual(d2.box, 2)

        d5 = deal_from_board_number(5, number_of_boxes=4)
        self.assertEqual(d5.id, 5)
        self.assertEqual(d5.box, 1)  # 5th deal cycles to box 1

    def test_dealer_vulnerability_from_box_uses_short_cycle(self) -> None:
        # With 4 boxes, cycle length is 4: use first 4 entries of BOARD_DEAL_CYCLE
        for box in (1, 2, 3, 4):
            dealer, vuln = deal_dealer_vulnerability(box, 4)
            self.assertEqual((dealer, vuln), BOARD_DEAL_CYCLE[box - 1])
        # Box 5 with 4 boxes cycles to index 0
        self.assertEqual(deal_dealer_vulnerability(5, 4), BOARD_DEAL_CYCLE[0])

    def test_deal_from_board_number_zero_raises(self) -> None:
        with self.assertRaises(ValueError):
            deal_from_board_number(0)

    def test_deal_from_board_number_negative_raises(self) -> None:
        with self.assertRaises(ValueError):
            deal_from_board_number(-1)


class BoxForDealTests(unittest.TestCase):
    """box_for_deal(deal_number, number_of_boxes) cycles 1..number_of_boxes."""

    def test_one_box(self) -> None:
        self.assertEqual(box_for_deal(1, 1), 1)
        self.assertEqual(box_for_deal(2, 1), 1)

    def test_three_boxes_cycle(self) -> None:
        self.assertEqual(box_for_deal(1, 3), 1)
        self.assertEqual(box_for_deal(2, 3), 2)
        self.assertEqual(box_for_deal(3, 3), 3)
        self.assertEqual(box_for_deal(4, 3), 1)
        self.assertEqual(box_for_deal(5, 3), 2)

    def test_invalid_number_of_boxes_raises(self) -> None:
        with self.assertRaises(ValueError):
            box_for_deal(1, 0)


class DealDealerVulnerabilityTests(unittest.TestCase):
    def test_short_cycle_four_boxes(self) -> None:
        """With 4 boxes, dealer/vuln use first 4 entries of standard cycle."""
        for box in range(1, 5):
            dealer, vuln = deal_dealer_vulnerability(box, 4)
            self.assertEqual((dealer, vuln), BOARD_DEAL_CYCLE[box - 1])
        self.assertEqual(deal_dealer_vulnerability(5, 4), BOARD_DEAL_CYCLE[0])

    def test_full_cycle_sixteen_boxes(self) -> None:
        for i in range(16):
            dealer, vuln = deal_dealer_vulnerability(i + 1, 16)
            self.assertEqual((dealer, vuln), BOARD_DEAL_CYCLE[i])

    def test_invalid_number_of_boxes_raises(self) -> None:
        with self.assertRaises(ValueError):
            deal_dealer_vulnerability(1, 0)


class Standard16BoardDealSequenceTests(unittest.TestCase):
    def test_first_16_boards_follow_standard_rotation_with_16_boxes(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=1, number_of_boxes=16)
        for i in range(16):
            d = next(gen)
            self.assertEqual(d.id, i + 1)
            self.assertEqual(d.box, i + 1)
            expected_dealer, expected_vul = BOARD_DEAL_CYCLE[i]
            dealer, vuln = deal_dealer_vulnerability(d.box, 16)
            self.assertEqual(dealer, expected_dealer)
            self.assertEqual(vuln, expected_vul)

    def test_start_id_zero_raises(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=0)
        with self.assertRaises(ValueError) as ctx:
            next(gen)
        self.assertIn("start_id", str(ctx.exception))

    def test_custom_start_id(self) -> None:
        gen = standard_16_board_deal_sequence(start_id=17, number_of_boxes=16)
        d = next(gen)
        self.assertEqual(d.id, 17)
        self.assertEqual(d.box, 1)  # (17-1) % 16 + 1
        dealer, vuln = deal_dealer_vulnerability(d.box, 16)
        self.assertEqual(dealer, "N")
        self.assertEqual(vuln, "None")

    def test_dealer_starts_from_n_clockwise_every_four_boards(self) -> None:
        """With 16 boxes, every block of 4 consecutive boards has dealer N,E,S,W."""
        for start in (1, 5, 9, 13, 17, 33):
            with self.subTest(start=start):
                for offset in range(4):
                    d = deal_from_board_number(start + offset, number_of_boxes=16)
                    dealer, _ = deal_dealer_vulnerability(d.box, 16)
                    self.assertEqual(
                        dealer,
                        DECLARERS[offset],
                        f"Board {d.id} box {d.box}: expected dealer {DECLARERS[offset]}, got {dealer}",
                    )

    def test_each_cycle_of_four_has_all_four_vulnerabilities_once(self) -> None:
        """With 16 boxes, every block of 4 consecutive boards has each vuln once."""
        expected_vuls = set(VULNERABILITIES)
        for start in (1, 5, 9, 13, 17, 21, 33):
            with self.subTest(start=start):
                vuls = [
                    deal_dealer_vulnerability(
                        deal_from_board_number(start + i, number_of_boxes=16).box, 16
                    )[1]
                    for i in range(4)
                ]
                self.assertEqual(
                    set(vuls),
                    expected_vuls,
                    f"Boards {start}-{start+3}: got {vuls}",
                )


if __name__ == "__main__":
    unittest.main()
