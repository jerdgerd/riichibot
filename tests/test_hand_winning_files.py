"""
Verifies the corrected Hand.get_winning_tiles() behaviour on a classical
'one-away' hand: 111m 222p 333s EEE 4s → waiting on 4s.
"""

from src.game.hand import Hand
from tiles.tile import Suit, Tile, Wind


def build_hand():
    h = Hand()
    tiles = [
        *(Tile(Suit.MANZU, 2) for _ in range(3)),
        *(Tile(Suit.PINZU, 2) for _ in range(3)),
        *(Tile(Suit.SOUZU, 7) for _ in range(3)),
        *(Tile(Suit.WIND, wind=Wind.EAST) for _ in range(3)),
        Tile(Suit.SOUZU, 4),
    ]
    for t in tiles:
        h.add_tile(t)
    return h


def test_waiting_on_four_sou():
    hand = build_hand()
    waits = hand.get_winning_tiles()
    four_sou = Tile(Suit.SOUZU, 4)
    print(waits)
    assert four_sou in waits
    # should be *exactly* one winning tile in this pattern
    assert len(waits) == 1
