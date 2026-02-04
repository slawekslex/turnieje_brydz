"""Unit tests for bridge scoring (standard duplicate)."""

import pytest

from bridge.scoring import compute_score, points_to_imp, calculate_deal_imp_scores


class ScoringInvalidInputTests:
    """compute_score returns None for invalid inputs."""

    def test_invalid_contract_returns_none(self):
        assert compute_score("", "N", 9, "None") is None
        assert compute_score("8S", "N", 10, "None") is None
        assert compute_score("3X", "N", 9, "None") is None

    def test_invalid_declarer_returns_none(self):
        assert compute_score("3NT", "", 9, "None") is None
        assert compute_score("3NT", "X", 9, "None") is None
        assert compute_score("3NT", "  ", 9, "None") is None

    def test_invalid_tricks_returns_none(self):
        assert compute_score("3NT", "N", -1, "None") is None
        assert compute_score("3NT", "N", 14, "None") is None
        assert compute_score("3NT", "N", "nine", "None") is None
        assert compute_score("3NT", "N", None, "None") is None

    def test_valid_tricks_0_to_13_accepted(self):
        assert compute_score("1NT", "N", 0, "None") is not None
        assert compute_score("7NT", "N", 13, "None") is not None


class ScoringMadeContractPartScoreTests:
    """Part scores (contract points < 100): 50 bonus."""

    def test_1nt_7_tricks_ns_none_vul(self):
        # 1NT = 40, 7 tricks = 1+6, made. 40 + 50 = 90
        ns, ew = compute_score("1NT", "N", 7, "None")
        assert ns == 90 and ew == -90

    def test_2c_8_tricks_ns(self):
        # 2C = 40, made. 40 + 50 = 90
        ns, ew = compute_score("2C", "N", 8, "None")
        assert ns == 90 and ew == -90

    def test_2s_8_tricks_ew(self):
        # 2S = 60, + 50 part score = 110; EW declarer so NS = -110
        ns, ew = compute_score("2S", "E", 8, "None")
        assert ns == -110 and ew == 110

    def test_3d_9_tricks_part_score(self):
        # 3D = 20+20+20 = 60, + 50
        ns, ew = compute_score("3D", "S", 9, "None")
        assert ns == 110 and ew == -110


class ScoringMadeContractGameTests:
    """Game (contract points >= 100): 300 non-vul, 500 vul."""

    def test_3nt_9_tricks_none_vul(self):
        # 3NT = 40+30+30 = 100, game. 100 + 300 = 400
        ns, ew = compute_score("3NT", "N", 9, "None")
        assert ns == 400 and ew == -400

    def test_4s_10_tricks_none_vul(self):
        # 4S = 30*4 = 120, 120 + 300 = 420
        ns, ew = compute_score("4S", "N", 10, "None")
        assert ns == 420 and ew == -420

    def test_3nt_9_tricks_ns_vulnerable(self):
        ns, ew = compute_score("3NT", "N", 9, "N-S")
        assert ns == 600 and ew == -600  # 100 + 500

    def test_4h_10_tricks_both_vul(self):
        ns, ew = compute_score("4H", "S", 10, "Both")
        assert ns == 620 and ew == -620  # 120 + 500


class ScoringOvertricksTests:
    """Overtricks: same as trick value undoubled; doubled 100/200, xx 200/400."""

    def test_3nt_10_tricks_one_overtrick(self):
        # 3NT made + 1 overtrick: 100 + 30 + 300 = 430
        ns, ew = compute_score("3NT", "N", 10, "None")
        assert ns == 430 and ew == -430

    def test_2s_doubled_9_tricks_one_overtrick_none_vul(self):
        # 2Sx = 60*2 = 120, overtrick 100, game 300, double bonus 50 -> 120+100+300+50 = 570
        ns, ew = compute_score("2Sx", "N", 9, "None")
        assert ns == 570 and ew == -570

    def test_2s_doubled_9_tricks_one_overtrick_vul(self):
        # overtrick vul = 200; 120 + 200 + 500 + 50 = 870
        ns, ew = compute_score("2Sx", "N", 9, "N-S")
        assert ns == 870 and ew == -870


class ScoringSlamGrandTests:
    """6-level: 500 non-vul, 750 vul; 7-level: 1000 non-vul, 1500 vul."""

    def test_6nt_12_tricks_none_vul(self):
        # 6NT = 40+30*5 = 190, + 300 (game) + 500 (slam) = 990
        ns, ew = compute_score("6NT", "N", 12, "None")
        assert ns == 990 and ew == -990

    def test_6nt_12_tricks_vul(self):
        ns, ew = compute_score("6NT", "N", 12, "Both")
        assert ns == 1440 and ew == -1440  # 190 + 500 + 750

    def test_7nt_13_tricks_none_vul(self):
        # 7NT = 220, + 300 (game) + 1000 (grand) = 1520
        ns, ew = compute_score("7NT", "N", 13, "None")
        assert ns == 1520 and ew == -1520

    def test_7nt_13_tricks_vul(self):
        # 7NT = 220, + 500 (game) + 1500 (grand) = 2220
        ns, ew = compute_score("7NT", "N", 13, "N-S")
        assert ns == 2220 and ew == -2220


class ScoringUndertricksTests:
    """Undertricks: 50 each non-vul, 100 each vul; doubled/redoubled scale."""

    def test_3nt_8_tricks_one_undertrick_none_vul(self):
        # Defenders (EW) get 50
        ns, ew = compute_score("3NT", "N", 8, "None")
        assert ns == -50 and ew == 50

    def test_3nt_7_tricks_two_undertricks_none_vul(self):
        ns, ew = compute_score("3NT", "N", 7, "None")
        assert ns == -100 and ew == 100

    def test_3nt_8_tricks_one_undertrick_vul(self):
        ns, ew = compute_score("3NT", "N", 8, "N-S")
        assert ns == -100 and ew == 100

    def test_4s_doubled_one_undertrick_none_vul(self):
        # Doubled: 100 first, then 200 each. 1 undertrick = 100
        ns, ew = compute_score("4Sx", "N", 9, "None")
        assert ns == -100 and ew == 100

    def test_4s_doubled_two_undertricks_none_vul(self):
        # 100 + 200 = 300
        ns, ew = compute_score("4Sx", "N", 8, "None")
        assert ns == -300 and ew == 300

    def test_4s_doubled_one_undertrick_vul(self):
        # 200 per undertrick
        ns, ew = compute_score("4Sx", "N", 9, "N-S")
        assert ns == -200 and ew == 200

    def test_4s_redoubled_two_undertricks_none_vul(self):
        # 200 + 400 = 600
        ns, ew = compute_score("4Sxx", "N", 8, "None")
        assert ns == -600 and ew == 600


class ScoringDeclarerSideTests:
    """EW as declarer: NS gets negative when EW makes, positive when EW fails."""

    def test_3nt_9_tricks_ew_declarer(self):
        ns, ew = compute_score("3NT", "E", 9, "None")
        assert ns == -400 and ew == 400

    def test_3nt_8_tricks_ew_declarer_undertrick(self):
        ns, ew = compute_score("3NT", "W", 8, "None")
        assert ns == 50 and ew == -50


class ScoringVulnerabilityParsingTests:
    """Vulnerability string is normalized (strip, case)."""

    def test_e_w_vul_ew_declarer_is_vul(self):
        ns, ew = compute_score("3NT", "E", 9, "E-W")
        assert ns == -600 and ew == 600  # vul game

    def test_n_s_vul_ns_declarer_is_vul(self):
        ns, ew = compute_score("3NT", "S", 9, "N-S")
        assert ns == 600 and ew == -600

    def test_both_vul_any_declarer(self):
        ns, ew = compute_score("3NT", "E", 9, "Both")
        assert ns == -600 and ew == 600


class ScoringRpbridgeTableTests:
    """
    Reference scores from Richard Pavlicek's duplicate bridge table.
    http://www.rpbridge.net/2y67.htm
    Scores are for declaring side; we test with declarer N so ns_score = table value.
    """

    def _check(self, contract: str, tricks: int, vul: str, expected_ns: int) -> None:
        ns, ew = compute_score(contract, "N", tricks, vul)
        assert ns == expected_ns and ew == -expected_ns

    # --- Minors (C, D) undoubled, NV ---
    def test_1c_made_1_nv(self):
        self._check("1C", 7, "None", 70)

    def test_1d_made_2_nv(self):
        self._check("1D", 8, "None", 90)

    def test_1c_made_4_nv(self):
        self._check("1C", 10, "None", 130)

    def test_2d_made_2_nv(self):
        self._check("2D", 8, "None", 90)

    def test_2d_made_5_nv(self):
        self._check("2D", 11, "None", 150)

    def test_3c_made_3_nv(self):
        self._check("3C", 9, "None", 110)

    def test_4d_made_4_nv(self):
        self._check("4D", 10, "None", 130)

    # --- Majors (H, S) undoubled, NV ---
    def test_1h_made_1_nv(self):
        self._check("1H", 7, "None", 80)

    def test_1s_made_2_nv(self):
        self._check("1S", 8, "None", 110)

    def test_2h_made_2_nv(self):
        self._check("2H", 8, "None", 110)

    def test_2s_made_4_nv(self):
        self._check("2S", 10, "None", 170)

    def test_3h_made_3_nv(self):
        self._check("3H", 9, "None", 140)

    def test_4s_made_4_nv(self):
        self._check("4S", 10, "None", 420)  # game

    def test_4h_made_5_nv(self):
        self._check("4H", 11, "None", 450)

    # --- NT undoubled ---
    def test_1nt_made_1_nv(self):
        self._check("1NT", 7, "None", 90)

    def test_1nt_made_3_nv(self):
        self._check("1NT", 9, "None", 150)

    def test_2nt_made_2_nv(self):
        self._check("2NT", 8, "None", 120)

    def test_2nt_made_4_nv(self):
        self._check("2NT", 10, "None", 180)

    def test_3nt_made_3_nv(self):
        self._check("3NT", 9, "None", 400)

    def test_3nt_made_3_vul(self):
        self._check("3NT", 9, "N-S", 600)

    def test_3nt_made_4_nv(self):
        self._check("3NT", 10, "None", 430)

    def test_3nt_made_4_vul(self):
        self._check("3NT", 10, "N-S", 630)

    def test_3nt_made_6_nv(self):
        self._check("3NT", 12, "None", 490)

    def test_3nt_made_7_nv(self):
        self._check("3NT", 13, "None", 520)

    def test_4nt_made_4_nv(self):
        self._check("4NT", 10, "None", 430)

    def test_4nt_made_5_vul(self):
        self._check("4NT", 11, "N-S", 660)

    def test_5c_made_5_nv(self):
        self._check("5C", 11, "None", 400)

    def test_5c_made_5_vul(self):
        self._check("5C", 11, "N-S", 600)

    def test_5c_made_7_nv(self):
        self._check("5C", 13, "None", 440)

    def test_5h_made_5_nv(self):
        self._check("5H", 11, "None", 450)

    def test_5h_made_6_vul(self):
        self._check("5H", 12, "N-S", 680)

    def test_5nt_made_5_nv(self):
        self._check("5NT", 11, "None", 460)

    def test_5nt_made_7_vul(self):
        self._check("5NT", 13, "N-S", 720)

    # --- Slams (table: 6x made 6/7) ---
    def test_6c_made_6_nv(self):
        self._check("6C", 12, "None", 920)

    def test_6c_made_6_vul(self):
        self._check("6C", 12, "N-S", 1370)

    def test_6c_made_7_nv(self):
        self._check("6C", 13, "None", 940)

    def test_6d_made_7_vul(self):
        self._check("6D", 13, "N-S", 1390)

    def test_6h_made_6_nv(self):
        self._check("6H", 12, "None", 980)

    def test_6h_made_6_vul(self):
        self._check("6H", 12, "N-S", 1430)

    def test_6h_made_7_nv(self):
        self._check("6H", 13, "None", 1010)

    def test_6s_made_7_vul(self):
        self._check("6S", 13, "N-S", 1460)

    def test_6nt_made_6_nv(self):
        self._check("6NT", 12, "None", 990)

    def test_6nt_made_6_vul(self):
        self._check("6NT", 12, "N-S", 1440)

    def test_6nt_made_7_nv(self):
        self._check("6NT", 13, "None", 1020)

    def test_6nt_made_7_vul(self):
        self._check("6NT", 13, "N-S", 1470)

    # --- Grand slams ---
    def test_7c_made_7_nv(self):
        self._check("7C", 13, "None", 1440)

    def test_7c_made_7_vul(self):
        self._check("7C", 13, "N-S", 2140)

    def test_7d_made_7_nv(self):
        self._check("7D", 13, "None", 1440)

    def test_7h_made_7_nv(self):
        self._check("7H", 13, "None", 1510)

    def test_7h_made_7_vul(self):
        self._check("7H", 13, "N-S", 2210)

    def test_7s_made_7_nv(self):
        self._check("7S", 13, "None", 1510)

    def test_7nt_made_7_nv(self):
        self._check("7NT", 13, "None", 1520)

    def test_7nt_made_7_vul(self):
        self._check("7NT", 13, "N-S", 2220)

    # --- Undertricks (table: "down N" = defenders get points; declarer gets negative) ---
    def test_any_down_1_nv(self):
        ns, ew = compute_score("3NT", "N", 8, "None")
        assert ns == -50 and ew == 50

    def test_any_down_1_vul(self):
        ns, ew = compute_score("3NT", "N", 8, "N-S")
        assert ns == -100 and ew == 100

    def test_any_down_2_nv(self):
        ns, ew = compute_score("3NT", "N", 7, "None")
        assert ns == -100 and ew == 100

    def test_any_down_2_vul(self):
        ns, ew = compute_score("4S", "N", 8, "N-S")
        assert ns == -200 and ew == 200

    def test_any_down_3_nv(self):
        ns, ew = compute_score("3NT", "N", 6, "None")
        assert ns == -150 and ew == 150

    def test_any_down_3_vul(self):
        ns, ew = compute_score("3NT", "N", 6, "N-S")
        assert ns == -300 and ew == 300

    def test_any_down_4_nv(self):
        # 2S needs 8 tricks; 4 tricks taken = 4 undertricks = 200 to defenders
        ns, ew = compute_score("2S", "N", 4, "None")
        assert ns == -200 and ew == 200

    def test_any_down_5_vul(self):
        ns, ew = compute_score("4H", "N", 5, "N-S")
        assert ns == -500 and ew == 500

    # --- Doubled undertricks (NV X / Vul X columns) ---
    def test_doubled_down_1_nv(self):
        ns, ew = compute_score("3NTx", "N", 8, "None")
        assert ns == -100 and ew == 100

    def test_doubled_down_1_vul(self):
        ns, ew = compute_score("3NTx", "N", 8, "N-S")
        assert ns == -200 and ew == 200

    def test_doubled_down_2_nv(self):
        ns, ew = compute_score("4Sx", "N", 8, "None")
        assert ns == -300 and ew == 300

    def test_doubled_down_2_vul(self):
        ns, ew = compute_score("4Sx", "N", 8, "N-S")
        assert ns == -500 and ew == 500

    def test_doubled_down_3_nv(self):
        ns, ew = compute_score("3NTx", "N", 6, "None")
        assert ns == -500 and ew == 500

    def test_doubled_down_3_vul(self):
        ns, ew = compute_score("3NTx", "N", 6, "N-S")
        assert ns == -800 and ew == 800

    def test_doubled_down_4_nv(self):
        # 2H needs 8 tricks; 4 tricks = 4 undertricks. NV X: 100+200+200+300 = 800
        ns, ew = compute_score("2Hx", "N", 4, "None")
        assert ns == -800 and ew == 800

    # --- Redoubled undertricks (NV XX / Vul XX) ---
    def test_redoubled_down_1_nv(self):
        ns, ew = compute_score("3NTxx", "N", 8, "None")
        assert ns == -200 and ew == 200

    def test_redoubled_down_1_vul(self):
        ns, ew = compute_score("3NTxx", "N", 8, "N-S")
        assert ns == -400 and ew == 400

    def test_redoubled_down_2_nv(self):
        ns, ew = compute_score("4Sxx", "N", 8, "None")
        assert ns == -600 and ew == 600

    def test_redoubled_down_2_vul(self):
        ns, ew = compute_score("4Sxx", "N", 8, "N-S")
        assert ns == -1000 and ew == 1000

    def test_redoubled_down_3_nv(self):
        ns, ew = compute_score("3NTxx", "N", 6, "None")
        assert ns == -1000 and ew == 1000

    def test_redoubled_down_3_vul(self):
        ns, ew = compute_score("3NTxx", "N", 6, "N-S")
        assert ns == -1600 and ew == 1600

    # --- Doubled made (sample from table: 2H/2S made 2 NV X = 470, Vul X = 670) ---
    def test_2s_doubled_made_2_nv(self):
        self._check("2Sx", 8, "None", 470)

    def test_2s_doubled_made_2_vul(self):
        self._check("2Sx", 8, "N-S", 670)

    def test_3nt_doubled_made_3_nv(self):
        self._check("3NTx", 9, "None", 550)

    def test_3nt_doubled_made_3_vul(self):
        self._check("3NTx", 9, "N-S", 750)

    def test_4h_doubled_made_4_nv(self):
        self._check("4Hx", 10, "None", 590)

    def test_4h_doubled_made_4_vul(self):
        self._check("4Hx", 10, "N-S", 790)

    def test_6nt_doubled_made_6_nv(self):
        self._check("6NTx", 12, "None", 1230)

    def test_6nt_doubled_made_6_vul(self):
        self._check("6NTx", 12, "N-S", 1680)

    def test_7nt_doubled_made_7_nv(self):
        self._check("7NTx", 13, "None", 1790)

    def test_7nt_doubled_made_7_vul(self):
        self._check("7NTx", 13, "N-S", 2490)


class PointsToImpTests:
    """points_to_imp converts point difference to IMP using standard table."""

    def test_zero_and_small_difference(self):
        assert points_to_imp(0) == 0
        assert points_to_imp(10) == 0

    def test_20_to_40_gives_1(self):
        assert points_to_imp(20) == 1
        assert points_to_imp(40) == 1

    def test_50_to_80_gives_2(self):
        assert points_to_imp(50) == 2
        assert points_to_imp(80) == 2

    def test_90_to_120_gives_3(self):
        assert points_to_imp(90) == 3
        assert points_to_imp(120) == 3

    def test_negative_difference_uses_absolute_value(self):
        assert points_to_imp(-20) == 1
        assert points_to_imp(-100) == 3

    def test_large_difference_caps_at_24(self):
        assert points_to_imp(4000) == 24
        assert points_to_imp(10000) == 24

    def test_boundaries_11_and_41(self):
        assert points_to_imp(11) == 1
        assert points_to_imp(41) == 2


class CalculateDealImpScoresTests:
    """calculate_deal_imp_scores: datum = avg rounded to nearest 10, then IMP per table."""

    def test_empty_scores_returns_empty(self):
        assert calculate_deal_imp_scores([]) == []

    def test_single_table_zero_imp(self):
        # One table: datum = 100, diff = 0 -> (0, 0)
        assert calculate_deal_imp_scores([100]) == [(0, 0)]

    def test_two_tables_same_score_both_zero(self):
        # Datum = 150, both diffs 0
        assert calculate_deal_imp_scores([150, 150]) == [(0, 0), (0, 0)]

    def test_two_tables_100_apart(self):
        # Scores 100 and 200: avg=150, datum=150. Diffs  -50 and +50.
        # 50 is 2 IMP. So (-2, +2) and (+2, -2)
        result = calculate_deal_imp_scores([100, 200])
        assert result == [(-2, 2), (2, -2)]

    def test_datum_rounded_to_nearest_10(self):
        # 90, 100, 110 -> avg 100, datum 100. All diffs -10, 0, 10 -> 0 IMP
        result = calculate_deal_imp_scores([90, 100, 110])
        assert result == [(0, 0), (0, 0), (0, 0)]

    def test_three_tables_one_above_two_below(self):
        # 0, 0, 300 -> avg 100, datum 100. Diffs -100, -100, +200.
        # 100 -> 3 IMP, 200 -> 5 IMP (170-210 range in standard table)
        result = calculate_deal_imp_scores([0, 0, 300])
        assert result == [(-3, 3), (-3, 3), (5, -5)]

    def test_ew_opposite_of_ns(self):
        result = calculate_deal_imp_scores([100, 500])
        # avg 300, datum 300. Diffs -200 -> 5 IMP, +200 -> 5 IMP
        # (-5, 5), (5, -5)
        for ns_imp, ew_imp in result:
            assert ew_imp == -ns_imp
