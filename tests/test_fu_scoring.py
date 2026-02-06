from src.game.hand import Hand
from src.game.rules import Yaku
from src.game.scoring import Scoring
from tiles.tile import Suit, Tile, Wind


def _tiles(*tiles):
    return list(tiles)


def test_pinfu_ron_fu_and_score():
    hand = Hand()
    hand.concealed_tiles = _tiles(
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
    )
    winning_tile = Tile(Suit.MANZU, 6)

    yaku_list = [Yaku("Pinfu", 1)]
    fu = Scoring.calculate_fu(
        hand=hand,
        winning_tile=winning_tile,
        is_tsumo=False,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
        yaku_list=yaku_list,
    )
    assert fu == 30

    score, payments = Scoring.calculate_score(
        yaku_list,
        is_dealer=False,
        is_tsumo=False,
        hand=hand,
        winning_tile=winning_tile,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
    )
    assert score == 1000
    assert payments == {"discarder": 1000}


def test_chiitoitsu_fixed_fu():
    hand = Hand()
    hand.concealed_tiles = _tiles(
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 2),
        Tile(Suit.SOUZU, 2),
        Tile(Suit.PINZU, 3),
        Tile(Suit.PINZU, 3),
        Tile(Suit.PINZU, 4),
        Tile(Suit.PINZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.MANZU, 5),
        Tile(Suit.MANZU, 6),
        Tile(Suit.MANZU, 6),
        Tile(Suit.WIND, wind=Wind.EAST),
    )
    winning_tile = Tile(Suit.WIND, wind=Wind.EAST)

    yaku_list = [Yaku("Chiitoitsu", 2)]
    fu = Scoring.calculate_fu(
        hand=hand,
        winning_tile=winning_tile,
        is_tsumo=False,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
        yaku_list=yaku_list,
    )
    assert fu == 25

    score, payments = Scoring.calculate_score(
        yaku_list,
        is_dealer=False,
        is_tsumo=False,
        hand=hand,
        winning_tile=winning_tile,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
    )
    assert score == 1600
    assert payments == {"discarder": 1600}


def test_meld_and_wait_fu():
    hand = Hand()
    hand.concealed_tiles = _tiles(
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 4),
        Tile(Suit.SOUZU, 5),
        Tile(Suit.MANZU, 6),
        Tile(Suit.MANZU, 7),
        Tile(Suit.MANZU, 8),
        Tile(Suit.WIND, wind=Wind.EAST),
    )
    winning_tile = Tile(Suit.WIND, wind=Wind.EAST)

    yaku_list = [Yaku("Yakuhai", 1)]
    fu = Scoring.calculate_fu(
        hand=hand,
        winning_tile=winning_tile,
        is_tsumo=False,
        seat_wind=Wind.EAST,
        round_wind=Wind.SOUTH,
        yaku_list=yaku_list,
    )
    assert fu == 50
