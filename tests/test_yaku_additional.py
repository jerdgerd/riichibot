import pytest

from src.game.hand import Hand
from src.game.rules import YakuChecker
from tiles.tile import Dragon, Suit, Tile, Wind


def _hand_with_tiles(tiles):
    hand = Hand()
    hand.concealed_tiles = tiles
    return hand


def test_sanshoku_doujun():
    tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.MANZU, 3),
        Tile(Suit.PINZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 3),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.SOUZU, 7),
        Tile(Suit.SOUZU, 7),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.MANZU, 6)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "sanshoku doujun" in names


def test_ittsu():
    tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.MANZU, 3),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.MANZU, 6),
        Tile(Suit.MANZU, 7),
        Tile(Suit.MANZU, 8),
        Tile(Suit.PINZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 3),
        Tile(Suit.SOUZU, 5),
        Tile(Suit.SOUZU, 5),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.MANZU, 9)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "ittsu" in names


def test_sanankou():
    tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.PINZU, 7),
        Tile(Suit.PINZU, 7),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.MANZU, 6)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "sanankou" in names


def test_chanta():
    tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.MANZU, 3),
        Tile(Suit.PINZU, 7),
        Tile(Suit.PINZU, 8),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.PINZU, 9)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "chanta" in names


def test_daisangen():
    tiles = [
        Tile(Suit.DRAGON, dragon=Dragon.WHITE),
        Tile(Suit.DRAGON, dragon=Dragon.WHITE),
        Tile(Suit.DRAGON, dragon=Dragon.WHITE),
        Tile(Suit.DRAGON, dragon=Dragon.GREEN),
        Tile(Suit.DRAGON, dragon=Dragon.GREEN),
        Tile(Suit.DRAGON, dragon=Dragon.GREEN),
        Tile(Suit.DRAGON, dragon=Dragon.RED),
        Tile(Suit.DRAGON, dragon=Dragon.RED),
        Tile(Suit.DRAGON, dragon=Dragon.RED),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.PINZU, 1),
        Tile(Suit.PINZU, 1),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.MANZU, 3)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "daisangen" in names


def test_suuankou_tsumo():
    tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 4),
        Tile(Suit.PINZU, 5),
        Tile(Suit.PINZU, 5),
    ]
    hand = _hand_with_tiles(tiles)
    winning = Tile(Suit.MANZU, 4)

    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
    )
    names = {y.name.lower() for y in yaku}
    assert "suuankou" in names
