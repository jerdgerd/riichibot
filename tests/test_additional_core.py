"""Additional test suite to raise coverage for core Riichi‑Mahjong logic
-------------------------------------------------------------------
Targets modules:
  * src.game.engine (MahjongEngine)
  * src.game.player (Player)
  * src.game.scoring (Scoring)
  * src.tiles.wall  (Wall)
  * Core data structures in src.tiles.tile & src.game.hand

These tests focus on **deterministic** behaviour that does not depend on random
wall draws where possible, monkey‑patching or manually manipulating objects to
reach specific game states.
"""

from __future__ import annotations

import importlib
import sys
import types

import pytest

# ────────────────────────────────────────────────────────────────────────────────
# Core imports
# ────────────────────────────────────────────────────────────────────────────────
from src.game.engine import MahjongEngine
from src.game.hand import Hand
from src.game.player import Player
from src.game.rules import Yaku
from src.game.scoring import Scoring
from tiles.tile import Dragon, Suit, Tile, Wind
from tiles.wall import Wall

# ────────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ────────────────────────────────────────────────────────────────────────────────


def _make_simple_tenpai_hand() -> list[Tile]:
    """Return a 13‑tile concealed hand that is one tile away from 4‑sou win.

    Pattern: 111m 222p 333s 4s EEE  (waiting on 4‑sou)
    """
    return [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.SOUZU, 4),  # lone 4‑sou – pair incomplete
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
    ]


# ────────────────────────────────────────────────────────────────────────────────
# Player‑level logic
# ────────────────────────────────────────────────────────────────────────────────


def test_player_can_call_chii_valid_and_invalid():
    """A player with 2‑sou & 4‑sou in hand should be able to chii 3‑sou from left."""
    player = Player("Tester", Wind.EAST)
    player.hand.concealed_tiles = [Tile(Suit.SOUZU, 2), Tile(Suit.SOUZU, 4)]

    discard = Tile(Suit.SOUZU, 3)

    # Valid call when the tile comes from the left
    sequences = player.can_call_chii(discard, from_left=True)
    expected_seq = [Tile(Suit.SOUZU, 2), discard, Tile(Suit.SOUZU, 4)]
    assert expected_seq in sequences

    # Invalid when the tile comes from another direction
    assert player.can_call_chii(discard, from_left=False) == []

    # Cannot chii honours
    honour = Tile(Suit.WIND, wind=Wind.EAST)
    assert player.can_call_chii(honour, True) == []


def test_player_pon_and_kan_detection():
    """Verify pon/kan pre‑conditions based on tile counts in hand."""
    base_tile = Tile(Suit.PINZU, 5)

    # Two copies – pon only
    player_pon = Player("Pon", Wind.SOUTH)
    player_pon.hand.concealed_tiles = [base_tile, Tile(Suit.PINZU, 5)]
    assert player_pon.can_call_pon(base_tile)
    assert not player_pon.can_call_kan(base_tile)

    # Three copies – kan available
    player_kan = Player("Kan", Wind.WEST)
    player_kan.hand.concealed_tiles = [base_tile] * 3
    assert player_kan.can_call_kan(base_tile)


def test_player_can_call_ron_respects_furiten():
    """Ron should be blocked when the hand is in furiten."""
    player = Player("Ron", Wind.NORTH)
    player.hand.concealed_tiles = _make_simple_tenpai_hand()

    winning_tile = Tile(Suit.SOUZU, 4)
    assert player.can_call_ron(winning_tile)

    player.hand.furiten_state = True
    assert not player.can_call_ron(winning_tile)


def test_player_declare_riichi_requires_points():
    player = Player("LowCash", Wind.EAST)
    player.score = 900  # below the 1‑k minimum
    with pytest.raises(ValueError):
        player.declare_riichi(turn=0)


# ────────────────────────────────────────────────────────────────────────────────
# Scoring logic
# ────────────────────────────────────────────────────────────────────────────────


def test_scoring_zero_han_raises():
    with pytest.raises(ValueError):
        Scoring.calculate_score([], is_dealer=False, is_tsumo=True)


def test_scoring_dealer_tsumo_single_han():
    yaku = [Yaku("Riichi", 1)]
    score, payments = Scoring.calculate_score(yaku, is_dealer=True, is_tsumo=True)

    # Base 1‑han → 1000, dealer multiplier ×1.5 → 1500, rounded stays 1500
    assert score == 1500
    assert payments == {"all": 500}


def test_scoring_non_dealer_ron_three_han():
    yaku = [Yaku("Example", 3)]
    score, payments = Scoring.calculate_score(yaku, is_dealer=False, is_tsumo=False)

    # 3‑han → base 3900, round unchanged
    assert score == 3900
    assert payments == {"discarder": 3900}


# ────────────────────────────────────────────────────────────────────────────────
# Wall & tile mechanics
# ────────────────────────────────────────────────────────────────────────────────


def test_wall_draw_and_dora_indicator():
    wall = Wall()
    start = wall.tiles_remaining()
    wall.draw_tile()
    assert wall.tiles_remaining() == start - 1

    initial_dora_count = len(wall.dora_indicators)
    wall.add_dora_indicator()
    assert len(wall.dora_indicators) == initial_dora_count + 1


# ────────────────────────────────────────────────────────────────────────────────
# Engine‑level logic (focused, monkey‑patched where needed)
# ────────────────────────────────────────────────────────────────────────────────


def test_engine_can_declare_riichi_positive_and_negative(monkeypatch):
    engine = MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)
    player = engine.players[0]

    # Positive scenario – monkey‑patch tenpai/closed conditions
    monkeypatch.setattr(player, "is_tenpai", lambda: True)
    monkeypatch.setattr(player.hand, "is_closed", lambda: True)
    player.score = 12000
    assert engine._can_declare_riichi(0)

    # Negative – insufficient points
    player.score = 500
    assert not engine._can_declare_riichi(0)


def test_engine_execute_discard_invalid_tile():
    engine = MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)
    player0 = engine.players[0]
    fake_tile_str = "9sou"  # Unlikely in opening hand of dealer

    result = engine.execute_action(0, "discard", tile=fake_tile_str)
    assert not result["success"]
    assert "Tile not found" in result["message"]


def test_engine_closed_kan_execution_success(monkeypatch):
    engine = MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)
    player0 = engine.players[0]

    # Replace dealer hand with four 9‑man tiles for a closed kan
    kan_tile = Tile(Suit.MANZU, 9)
    player0.hand.concealed_tiles = [kan_tile] * 4

    engine.current_player = 0  # Ensure it's dealer's turn
    result = engine.execute_closed_kan(0, str(kan_tile))
    assert result["success"]
    assert "closed kan" in result["message"]
    # Player should now have a meld representing the kan
    assert any(m.is_kan() for m in player0.hand.melds)


# ────────────────────────────────────────────────────────────────────────────────
# Safe / dangerous tile helpers
# ────────────────────────────────────────────────────────────────────────────────


def test_player_safe_tile_identification():
    p1 = Player("P1", Wind.EAST)
    p2 = Player("P2", Wind.SOUTH)

    safe_tile = Tile(Suit.PINZU, 1)
    p2.hand.discards.append(safe_tile)
    p1.hand.concealed_tiles = [safe_tile]

    safe_tiles = p1.get_safe_tiles([p2])
    assert safe_tile in safe_tiles
