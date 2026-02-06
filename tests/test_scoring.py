from src.game.rules import Yaku
from src.game.scoring import Scoring


def simple_hand(han: int):
    return [Yaku(f"Dummy{han}", han)]


def test_non_dealer_tsumo_three_han():
    score, payments = Scoring.calculate_score(
        simple_hand(3), is_dealer=False, is_tsumo=True
    )
    # 30-fu default, 3-han -> base 960; tsumo splits (dealer 2000, others 1000)
    assert score == 4000
    assert payments["dealer"] == 2000
    assert payments["non_dealer"] == 1000


def test_dealer_ron_mangan_equivalent():
    # 5 han -> mangan base 2000, dealer ron multiplier -> 12000
    score, payments = Scoring.calculate_score(
        [Yaku("ManganTest", 5)], is_dealer=True, is_tsumo=False
    )
    assert score == 12000
    assert payments["discarder"] == 12000
