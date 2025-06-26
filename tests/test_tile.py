#!/usr/bin/env python3
"""
Unit tests for Tile class
"""

import pytest

from tiles.tile import Dragon, Suit, Tile, Wind


class TestTile:
    def test_number_tile_creation(self):
        """Test valid number tile creation"""
        tile = Tile(Suit.PINZU, value=5)
        assert tile.suit == Suit.PINZU
        assert tile.value == 5
        assert not tile.is_red
        assert not tile.is_terminal()
        assert not tile.is_honor()

    def test_terminal_tiles(self):
        """Test terminal tile detection"""
        assert Tile(Suit.MANZU, value=1).is_terminal()
        assert Tile(Suit.MANZU, value=9).is_terminal()
        assert not Tile(Suit.MANZU, value=4).is_terminal()

    def test_honor_tile_creation(self):
        """Test honor tile creation and detection"""
        wind_tile = Tile(Suit.WIND, wind=Wind.EAST)
        dragon_tile = Tile(Suit.DRAGON, dragon=Dragon.RED)

        assert wind_tile.is_honor()
        assert dragon_tile.is_honor()

    def test_invalid_number_tile_value(self):
        """Test invalid number tile value raises error"""
        with pytest.raises(ValueError):
            Tile(Suit.SOUZU, value=0)
        with pytest.raises(ValueError):
            Tile(Suit.MANZU, value=10)
        with pytest.raises(TypeError):
            Tile(Suit.PINZU)  # No value

    def test_missing_wind_or_dragon(self):
        """Test wind/dragon tile missing enum raises error"""
        with pytest.raises(ValueError):
            Tile(Suit.WIND)
        with pytest.raises(ValueError):
            Tile(Suit.DRAGON)

    def test_terminal_or_honor(self):
        """Test is_terminal_or_honor logic"""
        t1 = Tile(Suit.SOUZU, value=1)
        t2 = Tile(Suit.PINZU, value=5)
        t3 = Tile(Suit.WIND, wind=Wind.NORTH)
        assert t1.is_terminal_or_honor()
        assert not t2.is_terminal_or_honor()
        assert t3.is_terminal_or_honor()

    def test_tile_str_representation(self):
        """Test string output of different tiles"""
        assert str(Tile(Suit.SOUZU, value=4)) == "4sou"
        assert str(Tile(Suit.SOUZU, value=5, is_red=True)) == "5rsou"
        assert str(Tile(Suit.WIND, wind=Wind.WEST)) == "west"
        assert str(Tile(Suit.DRAGON, dragon=Dragon.GREEN)) == "green"

    def test_tile_equality_and_hash(self):
        """Test tile equality and hashing"""
        t1 = Tile(Suit.MANZU, value=7)
        t2 = Tile(Suit.MANZU, value=7)
        t3 = Tile(Suit.MANZU, value=8)
        assert t1 == t2
        assert t1 != t3
        assert hash(t1) == hash(t2)

    def test_next_tile_numbered(self):
        """Test next tile for numbered suits"""
        tile = Tile(Suit.MANZU, value=8)
        next_tile = tile.next_tile()
        assert next_tile == Tile(Suit.MANZU, value=9)

        wrap_tile = Tile(Suit.MANZU, value=9)
        assert wrap_tile.next_tile() == Tile(Suit.MANZU, value=1)

    def test_next_tile_wind_and_dragon(self):
        """Test next tile for wind and dragon suits"""
        east = Tile(Suit.WIND, wind=Wind.EAST)
        assert east.next_tile() == Tile(Suit.WIND, wind=Wind.SOUTH)

        north = Tile(Suit.WIND, wind=Wind.NORTH)
        assert north.next_tile() == Tile(Suit.WIND, wind=Wind.EAST)

        green = Tile(Suit.DRAGON, dragon=Dragon.GREEN)
        assert green.next_tile() == Tile(Suit.DRAGON, dragon=Dragon.RED)

        white = Tile(Suit.DRAGON, dragon=Dragon.WHITE)
        assert white.next_tile() == Tile(Suit.DRAGON, dragon=Dragon.GREEN)


if __name__ == "__main__":
    pytest.main([__file__])
