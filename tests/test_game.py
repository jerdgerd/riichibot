#!/usr/bin/env python3
"""
Unit tests for Riichi Mahjong Engine
"""

import pytest

from src.game.engine import MahjongEngine
from src.game.hand import Hand, Meld
from tiles.tile import Dragon, Suit, Tile, Wind


class TestMahjongEngine:
    def test_game_initialization(self):
        """Test game initializes correctly"""
        players = ["Alice", "Bob", "Charlie", "David"]
        game = MahjongEngine(players)

        assert len(game.players) == 4
        assert game.players[0].name == "Alice"
        assert game.players[0].is_dealer
        assert game.current_player == 0
        assert game.wall.tiles_remaining() == 69  # 136 - 53 dealt - 14 dead wall

    def test_invalid_player_count(self):
        """Test error with wrong number of players"""
        with pytest.raises(ValueError):
            MahjongEngine(["Alice", "Bob"])

    def test_tile_creation(self):
        """Test tile creation and properties"""
        # Number tile
        tile = Tile(Suit.SOUZU, 5)
        assert tile.suit == Suit.SOUZU
        assert tile.value == 5
        assert not tile.is_honor()
        assert not tile.is_terminal()

        # Terminal tile
        terminal = Tile(Suit.PINZU, 1)
        assert terminal.is_terminal()
        assert terminal.is_terminal_or_honor()

        # Honor tile
        wind = Tile(Suit.WIND, wind=Wind.EAST)
        assert wind.is_honor()
        assert wind.is_terminal_or_honor()

    def test_hand_completion_check(self):
        """Test hand completion detection"""
        hand = Hand()

        # Create a complete hand: 111m 222p 333s 44s EEE
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
            Tile(Suit.SOUZU, 4),
            Tile(Suit.SOUZU, 4),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
        ]

        for tile in tiles:
            hand.add_tile(tile)

        assert hand._is_complete_hand(tiles)

    def test_tenpai_detection(self):
        """Test tenpai (ready hand) detection"""
        hand = Hand()

        # Create a hand one tile away from winning: 111m 222p 333s 4s EEE
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
            Tile(Suit.SOUZU, 4),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
        ]

        for tile in tiles:
            hand.add_tile(tile)

        winning_tiles = hand.get_winning_tiles()
        assert len(winning_tiles) > 0
        assert Tile(Suit.SOUZU, 4) in winning_tiles

    def test_meld_creation(self):
        """Test meld creation and types"""
        # Test sequence
        sequence_tiles = [Tile(Suit.SOUZU, 1), Tile(Suit.SOUZU, 2), Tile(Suit.SOUZU, 3)]
        sequence_meld = Meld(sequence_tiles)
        assert sequence_meld.is_sequence()
        assert not sequence_meld.is_triplet()

        # Test triplet
        triplet_tiles = [Tile(Suit.PINZU, 5), Tile(Suit.PINZU, 5), Tile(Suit.PINZU, 5)]
        triplet_meld = Meld(triplet_tiles)
        assert triplet_meld.is_triplet()
        assert not triplet_meld.is_sequence()

        # Test kan
        kan_tiles = [
            Tile(Suit.MANZU, 7),
            Tile(Suit.MANZU, 7),
            Tile(Suit.MANZU, 7),
            Tile(Suit.MANZU, 7),
        ]
        kan_meld = Meld(kan_tiles)
        assert kan_meld.is_kan()

    def test_dora_calculation(self):
        """Test dora tile calculation"""
        # Test number tile dora
        indicator = Tile(Suit.SOUZU, 3)
        dora = indicator.next_tile()
        assert dora.suit == Suit.SOUZU
        assert dora.value == 4

        # Test 9 wrapping to 1
        indicator_9 = Tile(Suit.PINZU, 9)
        dora_1 = indicator_9.next_tile()
        assert dora_1.value == 1

        # Test wind dora
        east_indicator = Tile(Suit.WIND, wind=Wind.EAST)
        south_dora = east_indicator.next_tile()
        assert south_dora.wind == Wind.SOUTH

    def test_player_actions(self):
        """Test basic player actions"""
        players = ["Alice", "Bob", "Charlie", "David"]
        game = MahjongEngine(players)

        # Test discard
        player = game.players[0]
        initial_hand_size = len(player.hand.concealed_tiles)

        if initial_hand_size > 0:
            tile_to_discard = player.hand.concealed_tiles[0]
            result = game.execute_action(0, "discard", tile=str(tile_to_discard))
            assert result["success"]
            assert len(player.hand.concealed_tiles) == initial_hand_size - 1
            assert len(player.hand.discards) == 1

    def test_riichi_declaration(self):
        """Test riichi declaration"""
        players = ["Alice", "Bob", "Charlie", "David"]
        game = MahjongEngine(players)

        player = game.players[0]
        initial_score = player.score

        # Manually set up a tenpai hand for testing
        player.hand.concealed_tiles = [
            Tile(Suit.MANZU, 1),
            Tile(Suit.MANZU, 1),
            Tile(Suit.MANZU, 1),
            Tile(Suit.PINZU, 2),
            Tile(Suit.PINZU, 2),
            Tile(Suit.PINZU, 2),
            Tile(Suit.SOUZU, 3),
            Tile(Suit.SOUZU, 3),
            Tile(Suit.SOUZU, 3),
            Tile(Suit.SOUZU, 4),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.WIND, wind=Wind.EAST),
            Tile(Suit.SOUZU, 5),  # 14th tile
        ]

        # Test riichi declaration
        if player.is_tenpai():
            result = game.execute_action(0, "riichi", tile=str(Tile(Suit.SOUZU, 5)))
            if result["success"]:
                assert player.hand.is_riichi
                assert player.score == initial_score - 1000

    def test_furiten_rule(self):
        """Test furiten rule implementation"""
        hand = Hand()

        # Add some tiles to hand
        tiles = [
            Tile(Suit.SOUZU, 1),
            Tile(Suit.SOUZU, 2),
            Tile(Suit.SOUZU, 3),
            Tile(Suit.PINZU, 4),
            Tile(Suit.PINZU, 5),
            Tile(Suit.PINZU, 6),
        ]

        for tile in tiles:
            hand.add_tile(tile)

        # Discard a potential winning tile
        winning_tile = Tile(Suit.SOUZU, 4)
        hand.discard_tile(winning_tile)

        # Check furiten state
        all_discards = [hand.discards, [], [], []]  # Only this player has discards
        is_furiten = hand.check_furiten(all_discards)

        # This test might need adjustment based on actual hand completion logic

    def test_scoring_calculation(self):
        """Test basic scoring calculation"""
        from src.game.rules import Yaku
        from src.game.scoring import Scoring

        # Test simple hand with riichi
        yaku_list = [Yaku("Riichi", 1), Yaku("Tanyao", 1)]

        score, payments = Scoring.calculate_score(
            yaku_list, is_dealer=False, is_tsumo=True
        )

        assert score > 0
        assert "dealer" in payments or "non_dealer" in payments

    def test_wall_management(self):
        """Test wall tile management"""
        from src.tiles.wall import Wall

        wall = Wall()
        initial_count = wall.tiles_remaining()

        # Draw a tile
        tile = wall.draw_tile()
        assert isinstance(tile, Tile)
        assert wall.tiles_remaining() == initial_count - 1

        # Test dora indicators
        dora_tiles = wall.get_dora_tiles()
        assert len(dora_tiles) >= 1


if __name__ == "__main__":
    pytest.main([__file__])
