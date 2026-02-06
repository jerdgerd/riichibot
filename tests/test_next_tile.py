from tiles.tile import Dragon, Suit, Tile, Wind


def test_number_wraps_nine_to_one():
    nine_pin = Tile(Suit.PINZU, 9)
    assert nine_pin.next_tile().value == 1 and nine_pin.next_tile().suit == Suit.PINZU


def test_wind_cycle():
    assert Tile(Suit.WIND, wind=Wind.WEST).next_tile().wind == Wind.NORTH
    assert Tile(Suit.WIND, wind=Wind.NORTH).next_tile().wind == Wind.EAST


def test_dragon_cycle():
    assert Tile(Suit.DRAGON, dragon=Dragon.WHITE).next_tile().dragon == Dragon.GREEN
