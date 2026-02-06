import pytest

from src.game.hand import Hand, Meld
from src.game.rules import YakuChecker
from tiles.tile import Suit, Tile, Wind


def _seq(suit: Suit, start: int):
    return [Tile(suit, start + i) for i in range(3)]


def build_closed_pinfu_tanyao_hand():
    """Closed 234s / 45m / 456p / 678s + pair 22p winning on 6m (ryanmen)"""
    h = Hand()
    tiles = (
        _seq(Suit.SOUZU, 2)
        + [Tile(Suit.MANZU, 4), Tile(Suit.MANZU, 5)]
        + _seq(Suit.PINZU, 4)
        + _seq(Suit.SOUZU, 6)
        + [Tile(Suit.PINZU, 2), Tile(Suit.PINZU, 2)]  # pair
    )
    for t in tiles:
        h.add_tile(t)
    return h, Tile(Suit.MANZU, 6)  # 6m completes 4-5-6m ryanmen


def test_pinfu_tanyao_detection():
    hand, winning = build_closed_pinfu_tanyao_hand()
    yaku = YakuChecker.check_all_yaku(
        hand,
        winning_tile=winning,
        is_tsumo=True,
        seat_wind=Wind.EAST,
        round_wind=Wind.EAST,
        dora_tiles=[],
        ura_dora_tiles=None,
    )
    names = {y.name.lower() for y in yaku}
    assert "tanyao" in names
    assert "pinfu" in names
    # closed hand + tsumo should add Menzen Tsumo
    assert "menzen tsumo" in names
    # no honor tiles, so yakuhai must **not** appear
    assert "yakuhai" not in names
