"""Extensive unit‑test suite covering every public and private method of
`src.game.engine.MahjongEngine`.

These tests rely on *monkeypatching* heavy dependencies (YakuChecker and
Scoring) so that the engine logic can be exercised in isolation without complex
hand‑evaluation logic.  Random elements (wall draws) are controlled by manual
state manipulation.
"""

from __future__ import annotations

import types

import pytest

from src.game.engine import GamePhase, MahjongEngine
from src.game.player import Player
from tiles.tile import Suit, Tile, Wind

# ────────────────────────────────────────────────────────────────────────────────
# Fixtures & Stubs
# ────────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def stub_scoring(monkeypatch):
    """Stub out YakuChecker and Scoring to deterministic values."""
    dummy_yaku = types.SimpleNamespace(name="Dummy", han=1)
    monkeypatch.setattr(
        "src.game.rules.YakuChecker.check_all_yaku",
        lambda *a, **kw: [dummy_yaku],
        raising=False,
    )
    monkeypatch.setattr(
        "src.game.scoring.Scoring.calculate_score",
        lambda *args, **kwargs: (
            1000,
            {"all": 333, "dealer": 500, "non_dealer": 250, "discarder": 1000},
        ),
        raising=False,
    )
    yield  # tests run here


def _fresh_engine() -> MahjongEngine:
    return MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)


def _make_four_of(tile: Tile) -> list[Tile]:
    return [tile, tile, tile, tile]


# ────────────────────────────────────────────────────────────────────────────────
# Tests per‑method
# ────────────────────────────────────────────────────────────────────────────────

# __init__ + _deal_initial_hands


def test_init_sets_up_players_and_phase():
    eng = _fresh_engine()
    assert len(eng.players) == 4
    assert eng.players[0].is_dealer
    assert eng.phase == GamePhase.PLAYING  # after dealing
    # dealer should have 14 tiles, others 13
    lengths = [len(p.hand.concealed_tiles) for p in eng.players]
    assert lengths[0] == 14 and all(l == 13 for l in lengths[1:])


# get_game_state


def test_get_game_state_contains_expected_keys():
    eng = _fresh_engine()
    state = eng.get_game_state()
    for key in ["phase", "current_player", "dealer", "players", "wall_tiles_remaining"]:
        assert key in state
    assert state["phase"] == "playing"
    assert len(state["players"]) == 4


# get_player_hand


def test_get_player_hand_reports_tenpai_and_riichi():
    eng = _fresh_engine()
    hand_data = eng.get_player_hand(0)
    # should always have concealed_tiles key etc.
    assert {
        "concealed_tiles",
        "melds",
        "winning_tiles",
        "is_tenpai",
        "can_riichi",
    }.issubset(hand_data)


# _can_declare_riichi


def test_can_declare_riichi_logic(monkeypatch):
    eng = _fresh_engine()
    p = eng.players[0]
    monkeypatch.setattr(p.hand, "is_closed", lambda: True)
    monkeypatch.setattr(p, "is_tenpai", lambda: True)
    p.score = 1500
    assert eng._can_declare_riichi(0)
    p.score = 900
    assert not eng._can_declare_riichi(0)


# get_valid_actions


def test_get_valid_actions_for_current_player(monkeypatch):
    eng = _fresh_engine()
    current = eng.current_player
    player = eng.players[current]
    # Ensure hand size 14 so discard is available
    if len(player.hand.concealed_tiles) == 13:
        player.draw_tile(player.hand.concealed_tiles[0])
    actions = eng.get_valid_actions(current)
    assert "discard" in actions


# _execute_discard & execute_action dispatcher


def test_execute_discard_flow():
    eng = _fresh_engine()
    p = eng.players[0]
    tile_to_disc = p.hand.concealed_tiles[0]
    res = eng.execute_action(0, "discard", tile=str(tile_to_disc))
    assert res["success"]
    assert eng.last_discard == tile_to_disc


# advance_turn


def test_advance_turn_draws_tile_and_rotates():
    eng = _fresh_engine()
    eng.last_discard = None  # so advance_turn will rotate
    first_player = eng.current_player
    eng.advance_turn()
    assert eng.current_player == (first_player + 1) % 4
    # new current player should have drawn a tile to reach 14
    assert len(eng.players[eng.current_player].hand.concealed_tiles) == 14


# start_new_round


def test_start_new_round_resets_state():
    eng = _fresh_engine()
    eng.start_new_round()
    assert eng.phase == GamePhase.PLAYING  # dealing done automatically
    assert eng.turn_number == 0


# advance_round


def test_advance_round_wind_rotation():
    eng = _fresh_engine()
    ended = eng.advance_round()
    # After first call dealer moves to 1, round wind stays EAST
    assert not ended
    assert eng.dealer == 1
    # Rotate until South round ends
    for _ in range(4):
        ended = eng.advance_round()
    assert ended  # south round completion ends game


# _handle_draw & is_game_over


def test_handle_draw_payments_and_phase(monkeypatch):
    eng = _fresh_engine()
    # Stub wall to appear empty so _handle_draw is called
    monkeypatch.setattr(eng.wall, "tiles_remaining", lambda: 0)
    result = eng.execute_action(0, "pass")
    assert result["game_ended"]
    assert eng.phase == GamePhase.ENDED


# _apply_tsumo_payments (indirect via _execute_tsumo)


def test_execute_tsumo_updates_scores(monkeypatch):
    eng = _fresh_engine()
    p = eng.players[0]

    # Force p into tsumo‑able state: hand size 14 & can_tsumo returns True
    monkeypatch.setattr(p, "can_tsumo", lambda: True)
    # ensure player has 14 tiles – already should as dealer, else draw
    res = eng.execute_action(0, "tsumo")
    assert res["success"] and eng.phase == GamePhase.ENDED


# _execute_ron


def test_execute_ron_success(monkeypatch):
    eng = _fresh_engine()
    discarder = eng.players[0]
    caller = eng.players[1]
    winning_tile = discarder.hand.concealed_tiles[0]

    # Move tile to last_discard
    eng.last_discard = winning_tile
    eng.last_discard_player = 0

    # Ensure caller believes it can ron
    monkeypatch.setattr(caller, "can_call_ron", lambda t: True)
    res = eng.execute_action(1, "ron")
    assert res["success"] and eng.phase == GamePhase.ENDED


# _execute_chii


def test_execute_chii_valid(monkeypatch):
    eng = _fresh_engine()
    # Prepare tiles 2‑3‑4 sou with player 1 able to chii 3‑sou from player 0
    two = Tile(Suit.SOUZU, 2)
    four = Tile(Suit.SOUZU, 4)
    three = Tile(Suit.SOUZU, 3)
    caller = eng.players[1]
    caller.hand.concealed_tiles = [two, four]

    eng.last_discard = three
    eng.last_discard_player = 0

    res = eng.execute_action(1, "chii", sequence=[str(two), str(four)])
    assert res["success"]
    assert any(m.is_sequence() for m in caller.hand.melds)


# _execute_pon


def test_execute_pon(monkeypatch):
    eng = _fresh_engine()
    t = Tile(Suit.PINZU, 5)
    eng.last_discard = t
    eng.last_discard_player = 0

    caller = eng.players[1]
    caller.hand.concealed_tiles = [t, t]  # two matching tiles
    monkeypatch.setattr(caller, "can_call_pon", lambda tile: True)

    res = eng.execute_action(1, "pon")
    assert res["success"]
    assert any(m.is_triplet() for m in caller.hand.melds)


# _execute_kan (open from discard)


def test_execute_open_kan(monkeypatch):
    eng = _fresh_engine()
    t = Tile(Suit.MANZU, 9)
    eng.last_discard = t
    eng.last_discard_player = 0
    caller = eng.players[1]
    caller.hand.concealed_tiles = [t, t, t]
    monkeypatch.setattr(caller, "can_call_kan", lambda tile: True)

    res = eng.execute_action(1, "kan")
    assert res["success"]
    assert any(m.is_kan() for m in caller.hand.melds)


# can_call_closed_kan & execute_closed_kan


def test_closed_kan_flow(monkeypatch):
    eng = _fresh_engine()
    eng.current_player = 0
    t = Tile(Suit.PINZU, 1)
    p = eng.players[0]
    p.hand.concealed_tiles = _make_four_of(t)

    # can_call_closed_kan should list tile
    assert str(t) in eng.can_call_closed_kan(0)

    res = eng.execute_closed_kan(0, str(t))
    assert res["success"]
    assert any(m.is_kan() for m in p.hand.melds)


# can_upgrade_pon_to_kan


def test_can_upgrade_pon_to_kan():
    eng = _fresh_engine()
    p = eng.players[0]
    t = Tile(Suit.SOUZU, 7)
    # create open pon meld
    pon_meld = p.hand.melds.append(
        types.SimpleNamespace(is_triplet=lambda: True, is_open=True, tiles=[t])
    )
    p.hand.concealed_tiles.append(t)  # 4th tile in hand
    up = eng.can_upgrade_pon_to_kan(0)
    assert str(t) in up


# get_safe_tiles_for_player & get_dangerous_tiles_for_player


def test_safe_and_dangerous_tiles_logic(monkeypatch):
    eng = _fresh_engine()

    safe_tile = Tile(Suit.MANZU, 1)
    danger_tile = Tile(Suit.MANZU, 9)

    player0, player1 = eng.players[:2]
    player1.hand.discards.append(safe_tile)
    player1.hand.concealed_tiles.append(danger_tile)

    monkeypatch.setattr(player1, "is_tenpai", lambda: True)
    monkeypatch.setattr(player1.hand, "get_winning_tiles", lambda: {danger_tile})

    assert str(safe_tile) in eng.get_safe_tiles_for_player(0)
    assert str(danger_tile) in eng.get_dangerous_tiles_for_player(0)


# get_game_log


def test_game_log_returns_state_snapshot():
    eng = _fresh_engine()
    log = eng.get_game_log()
    assert isinstance(log, list) and log[0]["action"] == "game_state"


# reset_game


def test_reset_game_restores_initial_conditions():
    eng = _fresh_engine()
    eng.players[0].score = 100
    eng.turn_number = 5
    eng.reset_game()
    assert eng.players[0].score == 25000
    assert eng.turn_number == 0
    assert eng.phase == GamePhase.PLAYING
