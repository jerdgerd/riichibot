from src.game.rules import Yaku
from src.game.scoring import Scoring


def simple_hand(han: int):
    return [Yaku(f"Dummy{han}", han)]


def test_non_dealer_tsumo_three_han():
    score, payments = Scoring.calculate_score(
        simple_hand(3), is_dealer=False, is_tsumo=True
    )
    # three han base points table → 3 900, then rounded up:
    assert score == 3900
    assert payments["dealer"] == score // 2
    assert payments["non_dealer"] == score // 4


def test_dealer_ron_mangan_equivalent():
    # 5 han → Mangan 8 000 base, dealer bonus *1.5 ≈ 12 000, round-up to 12 000
    score, payments = Scoring.calculate_score(
        [Yaku("ManganTest", 5)], is_dealer=True, is_tsumo=False
    )
    assert score == 12000
    assert payments["discarder"] == 12000
