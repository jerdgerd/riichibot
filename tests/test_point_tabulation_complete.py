from src.game.hand import Hand
from src.game.rules import Yaku
from src.game.scoring import Scoring
from tiles.tile import Suit, Tile, Wind


def test_pinfu_tsumo_uses_20_fu_and_correct_payments():
    hand = Hand()
    hand.concealed_tiles = [
        Tile(Suit.SOUZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 4),
        Tile(Suit.PINZU, 3),
        Tile(Suit.PINZU, 4),
        Tile(Suit.PINZU, 5),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.SOUZU, 6),
        Tile(Suit.SOUZU, 7),
        Tile(Suit.SOUZU, 8),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
    ]
    winning_tile = Tile(Suit.MANZU, 6)

    yaku_list = [Yaku("Pinfu", 1), Yaku("Menzen Tsumo", 1)]

    fu = Scoring.calculate_fu(
        hand=hand,
        winning_tile=winning_tile,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
        yaku_list=yaku_list,
    )
    assert fu == 20

    score, payments = Scoring.calculate_score(
        yaku_list=yaku_list,
        is_dealer=False,
        is_tsumo=True,
        hand=hand,
        winning_tile=winning_tile,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
    )
    assert score == 1500
    assert payments == {"dealer": 700, "non_dealer": 400}


def test_honba_is_applied_to_ron_and_tsumo():
    ron_score, ron_payments = Scoring.calculate_score(
        yaku_list=[Yaku("Dummy", 3)],
        is_dealer=False,
        is_tsumo=False,
        honba=2,
    )
    assert ron_score == 4500
    assert ron_payments == {"discarder": 4500}

    tsumo_score, tsumo_payments = Scoring.calculate_score(
        yaku_list=[Yaku("Dummy", 1)],
        is_dealer=True,
        is_tsumo=True,
        honba=2,
    )
    assert tsumo_score == 2100
    assert tsumo_payments == {"all": 700}


def test_multiple_yakuman_stack_correctly():
    score, payments = Scoring.calculate_score(
        yaku_list=[Yaku("Daisuushii", 13), Yaku("Tsuuiisou", 13)],
        is_dealer=False,
        is_tsumo=False,
    )
    assert score == 64000
    assert payments == {"discarder": 64000}


def test_kazoe_yakuman_caps_to_single_yakuman():
    score, payments = Scoring.calculate_score(
        yaku_list=[Yaku("Chinitsu", 6), Yaku("Ryanpeikou", 3), Yaku("Dora", 4)],
        is_dealer=False,
        is_tsumo=False,
    )
    assert score == 32000
    assert payments == {"discarder": 32000}


def test_yakuman_ignores_extra_non_yakuman_han():
    score, payments = Scoring.calculate_score(
        yaku_list=[Yaku("Kokushi Musou", 13), Yaku("Dora", 8), Yaku("Riichi", 1)],
        is_dealer=False,
        is_tsumo=False,
    )
    assert score == 32000
    assert payments == {"discarder": 32000}
