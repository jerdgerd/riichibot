import types

from src.game.engine import GamePhase, MahjongEngine
from src.game.hand import Hand, Meld
from src.game.rules import Yaku
from tiles.tile import Suit, Tile, Wind


def make_engine():
    return MahjongEngine(["A", "B", "C", "D"])


def test_state_helpers_and_context(monkeypatch):
    e = make_engine()
    state = e.get_game_state()
    assert state["phase"] == "playing"
    hand = e.get_player_hand(0)
    assert "concealed_tiles" in hand and "can_riichi" in hand

    p = e.players[0]
    p.hand.is_riichi = True
    p.hand.ippatsu_eligible = True
    p.hand.riichi_turn = 0
    p.is_dealer = True
    e.turn_number = 0
    e.has_open_call = False
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    ctx = e._build_yaku_context(0, is_tsumo=True)
    assert ctx["is_ippatsu"] and ctx["is_double_riichi"] and ctx["is_tenhou"] and ctx["is_haitei"]


def test_has_yaku_and_chankan_helpers(monkeypatch):
    e = make_engine()
    tile = Tile(Suit.MANZU, 1)

    def fake_dora_only(*args, **kwargs):
        return [Yaku("Dora", 1)]

    def fake_real(*args, **kwargs):
        return [Yaku("Riichi", 1), Yaku("Dora", 1)]

    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", fake_dora_only)
    assert not e._has_yaku_for_win(e.players[0], tile, True)
    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", fake_real)
    assert e._has_yaku_for_win(e.players[0], tile, False)

    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: True)
    monkeypatch.setattr(e.players[2], "can_call_ron", lambda t: True)
    monkeypatch.setattr(e.players[3], "can_call_ron", lambda t: False)
    monkeypatch.setattr(e, "_has_yaku_for_win", lambda p, t, **kw: p is e.players[1])
    assert e._find_chankan_responders(tile, 0) == [1]


def test_get_valid_actions_branches(monkeypatch):
    e = make_engine()
    p0 = e.players[0]

    p0.hand.concealed_tiles = p0.hand.concealed_tiles[:14]
    p0.hand.last_drawn_tile = p0.hand.concealed_tiles[-1]
    monkeypatch.setattr(p0, "can_tsumo", lambda: True)
    monkeypatch.setattr(e, "_has_yaku_for_win", lambda *a, **k: True)
    monkeypatch.setattr(e, "can_call_closed_kan", lambda idx: ["1m"])
    monkeypatch.setattr(e, "can_upgrade_pon_to_kan", lambda idx: [])
    monkeypatch.setattr(e, "_can_declare_riichi", lambda idx: True)
    assert set(e.get_valid_actions(0)) == {"discard", "tsumo", "kan", "riichi"}

    p0.hand.concealed_tiles = p0.hand.concealed_tiles[:13]
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 1)
    monkeypatch.setattr(e.wall, "draw_tile", lambda: Tile(Suit.PINZU, 1))
    actions = e.get_valid_actions(0)
    assert "discard" in actions

    e.pending_chankan_tile = Tile(Suit.SOUZU, 5)
    e.pending_chankan_from = 0
    assert e.get_valid_actions(0) == []


def test_execute_action_routing_and_errors(monkeypatch):
    e = make_engine()
    monkeypatch.setattr(e, "_execute_discard", lambda i, t: {"success": True})
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 1)
    assert e.execute_action(0, "discard", tile="x")["success"]

    monkeypatch.setattr(e, "_execute_discard", lambda i, t: (_ for _ in ()).throw(RuntimeError("boom")))
    out = e.execute_action(0, "discard", tile="x")
    assert not out["success"] and "boom" in out["message"]

    assert "Unknown action" in e.execute_action(0, "xyz")["message"]


def test_discard_riichi_and_calls(monkeypatch):
    e = make_engine()
    t = e.players[0].hand.concealed_tiles[0]
    out = e._execute_discard(1, str(t))
    assert not out["success"]
    out = e._execute_discard(0, "9z")
    assert not out["success"]
    out = e._execute_discard(0, str(t))
    assert out["success"] and e.last_discard_player == 0

    monkeypatch.setattr(e, "_can_declare_riichi", lambda idx: False)
    assert not e._execute_riichi(0, str(e.players[0].hand.concealed_tiles[0]))["success"]


def test_tsumo_and_ron_paths(monkeypatch):
    e = make_engine()
    p = e.players[0]
    tile = p.hand.concealed_tiles[-1]
    p.hand.last_drawn_tile = tile

    monkeypatch.setattr(p, "can_tsumo", lambda: False)
    assert not e._execute_tsumo(0)["success"]

    monkeypatch.setattr(p, "can_tsumo", lambda: True)
    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", lambda *a, **k: [Yaku("Dora", 1)])
    assert not e._execute_tsumo(0)["success"]

    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", lambda *a, **k: [Yaku("Riichi", 1)])
    monkeypatch.setattr("src.game.engine.Scoring.calculate_score", lambda *a, **k: (1000, {"all": 500}))
    res = e._execute_tsumo(0)
    assert res["success"] and e.phase == GamePhase.ENDED

    e = make_engine()
    assert not e._execute_ron(1)["success"]
    e.last_discard = Tile(Suit.MANZU, 1)
    e.last_discard_player = 0
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: True)
    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", lambda *a, **k: [Yaku("Riichi", 1)])
    monkeypatch.setattr("src.game.engine.Scoring.calculate_score", lambda *a, **k: (1000, {}))
    assert e._execute_ron(1)["success"]


def test_pass_chii_pon_kan_related(monkeypatch):
    e = make_engine()
    t = Tile(Suit.MANZU, 2)
    e.pending_chankan_tile = t
    e.pending_chankan_from = 0
    e.pending_chankan_responders = {1}
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda tile: True)
    monkeypatch.setattr(e, "_perform_added_kan", lambda idx, tile: {"success": True, "message": "ok"})
    assert e._execute_pass(1)["success"]

    e = make_engine()
    assert not e._execute_chii(1, [str(Tile(Suit.MANZU, 1)), str(Tile(Suit.MANZU, 2))])["success"]
    e.last_discard = Tile(Suit.MANZU, 3)
    e.last_discard_player = 2
    assert not e._execute_chii(1, [str(Tile(Suit.MANZU, 1)), str(Tile(Suit.MANZU, 2))])["success"]

    e.last_discard_player = 0
    p1 = e.players[1]
    p1.hand.concealed_tiles = [Tile(Suit.MANZU, 1), Tile(Suit.MANZU, 2)] + p1.hand.concealed_tiles[2:]
    assert e._execute_chii(1, [str(Tile(Suit.MANZU, 1)), str(Tile(Suit.MANZU, 2))])["success"]

    e = make_engine()
    assert not e._execute_pon(1)["success"]
    e.last_discard = Tile(Suit.PINZU, 4)
    e.last_discard_player = 0
    monkeypatch.setattr(e.players[1], "can_call_pon", lambda tile: True)
    monkeypatch.setattr(e.players[1], "call_pon", lambda tile, who: None)
    assert e._execute_pon(1)["success"]

    e = make_engine()
    assert not e._execute_kan(1)["success"]


def test_closed_added_kan_and_riichi_kan_restrictions(monkeypatch):
    e = make_engine()
    p = e.players[0]
    tile = Tile(Suit.SOUZU, 6)
    p.hand.concealed_tiles = [tile, tile, tile, tile] + p.hand.concealed_tiles[4:]
    assert not e._execute_closed_or_added_kan(1, str(tile))["success"]
    assert not e._execute_closed_or_added_kan(0, None)["success"]
    assert not e._execute_closed_or_added_kan(0, "9z")["success"]

    monkeypatch.setattr(e, "_riichi_kan_allowed", lambda player, t: False)
    assert not e._execute_closed_or_added_kan(0, str(tile))["success"]

    monkeypatch.setattr(e, "_riichi_kan_allowed", lambda player, t: True)
    monkeypatch.setattr(p, "can_upgrade_pon_to_kan", lambda t: False)
    monkeypatch.setattr(p, "call_kan", lambda t: None)
    monkeypatch.setattr(e.wall, "add_dora_indicator", lambda: None)
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    assert e._execute_closed_or_added_kan(0, str(tile))["success"]

    # riichi restriction helper
    p.hand.is_riichi = True
    p.hand.concealed_tiles = [tile, tile, tile, tile]
    monkeypatch.setattr(p.hand, "get_winning_tiles_with_fixed_melds", lambda tiles, fixed_melds=0: [Tile(Suit.MANZU, 1)])
    assert e._riichi_kan_allowed(p, tile)


def test_round_flow_misc_and_reset(monkeypatch):
    e = make_engine()
    e.riichi_bets = 2
    e._apply_tsumo_payments(0, 0, {"all": 100})
    assert e.riichi_bets == 0

    e._update_honba_after_win(0)
    assert e.honba >= 1
    e.players[1].is_dealer = False
    e._update_honba_after_win(1)
    assert e.honba == 0

    monkeypatch.setattr(e.players[0], "is_tenpai", lambda: True)
    monkeypatch.setattr(e.players[1], "is_tenpai", lambda: False)
    monkeypatch.setattr(e.players[2], "is_tenpai", lambda: False)
    monkeypatch.setattr(e.players[3], "is_tenpai", lambda: False)
    out = e._handle_draw()
    assert out["game_ended"] and e.phase == GamePhase.ENDED

    e.last_discard = None
    before = e.current_player
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    e.advance_turn()
    assert e.current_player != before

    e.start_new_round()
    assert e.phase == GamePhase.PLAYING

    e.round_wind = Wind.SOUTH
    e.dealer = 3
    assert e.advance_round() is True

    e.players[0].score = -1
    assert e.is_game_over()

    ranks = e.get_final_rankings()
    assert ranks[0]["rank"] == 1

    e.players[0].hand.concealed_tiles = [Tile(Suit.MANZU, 1)]
    e.players[1].hand.discards = [Tile(Suit.MANZU, 1)]
    monkeypatch.setattr(e.players[1], "is_tenpai", lambda: False)
    assert e.get_safe_tiles_for_player(0) == [str(Tile(Suit.MANZU, 1))]
    assert e.get_dangerous_tiles_for_player(0) == []

    t = Tile(Suit.PINZU, 7)
    e.players[0].hand.concealed_tiles = [t, t, t, t]
    e.players[0].hand.is_riichi = False
    assert e.can_call_closed_kan(0) == [str(Tile(Suit.PINZU, 7))]

    e.players[0].hand.melds = [Meld([t, t, t], is_open=True)]
    e.players[0].hand.concealed_tiles = [t]
    assert e.can_upgrade_pon_to_kan(0) == [str(Tile(Suit.PINZU, 7))]

    assert not e.execute_closed_kan(1, str(t))["success"]
    assert not e.execute_closed_kan(0, "9z")["success"]
    e.players[0].hand.concealed_tiles = [t, t, t]
    assert not e.execute_closed_kan(0, str(t))["success"]

    e.players[0].hand.concealed_tiles = [t, t, t, t]
    monkeypatch.setattr(e.players[0], "call_kan", lambda x: None)
    monkeypatch.setattr(e.wall, "add_dora_indicator", lambda: None)
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    assert e.execute_closed_kan(0, str(t))["success"]

    assert e.get_game_log()[0]["action"] == "game_state"
    e.reset_game()
    assert e.phase == GamePhase.PLAYING and e.players[0].score == 25000

def test_execute_action_additional_routing_and_wall_draw(monkeypatch):
    e = make_engine()
    monkeypatch.setattr(e, "_execute_tsumo", lambda i: {"success": True})
    monkeypatch.setattr(e, "_execute_riichi", lambda i, t: {"success": True})
    monkeypatch.setattr(e, "_execute_chii", lambda i, s: {"success": True})
    monkeypatch.setattr(e, "_execute_pon", lambda i: {"success": True})
    monkeypatch.setattr(e, "_execute_kan", lambda i: {"success": True})
    monkeypatch.setattr(e, "_execute_closed_or_added_kan", lambda i, t: {"success": True})
    monkeypatch.setattr(e, "_execute_pass", lambda i: {"success": True})
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 1)
    assert e.execute_action(0, "tsumo")["success"]
    assert e.execute_action(0, "riichi", tile="x")["success"]
    assert e.execute_action(0, "chii", sequence=[])["success"]
    assert e.execute_action(0, "pon")["success"]
    e.last_discard = Tile(Suit.MANZU, 1)
    assert e.execute_action(0, "kan")["success"]
    e.last_discard = None
    assert e.execute_action(0, "kan", tile="x")["success"]
    assert e.execute_action(0, "pass")["success"]

    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    monkeypatch.setattr(e, "_handle_draw", lambda: {"success": True, "game_ended": True, "message": "draw"})
    assert e.execute_action(0, "pass")["game_ended"]


def test_remaining_engine_branches(monkeypatch):
    e = make_engine()
    # get_valid_actions non-current responder with ron/pon/kan/chii/pass
    e.current_player = 0
    e.last_discard_player = 0
    e.last_discard = Tile(Suit.MANZU, 3)
    p1 = e.players[1]
    monkeypatch.setattr(p1, "can_call_ron", lambda t: True)
    monkeypatch.setattr(e, "_has_yaku_for_win", lambda *a, **k: True)
    monkeypatch.setattr(p1, "can_call_pon", lambda t: True)
    monkeypatch.setattr(p1, "can_call_kan", lambda t: True)
    monkeypatch.setattr(p1, "can_call_chii", lambda t, from_left: True)
    actions = e.get_valid_actions(1)
    assert set(actions) == {"ron", "pon", "kan", "chii", "pass"}

    # current player with 13 tiles and empty wall hits branch
    p0 = e.players[0]
    p0.hand.concealed_tiles = p0.hand.concealed_tiles[:13]
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 0)
    assert e.get_valid_actions(0) == []

    # _execute_ron no-yaku branch
    e = make_engine()
    e.last_discard = Tile(Suit.PINZU, 5)
    e.last_discard_player = 0
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: True)
    monkeypatch.setattr("src.game.engine.YakuChecker.check_all_yaku", lambda *a, **k: [Yaku("Dora", 2)])
    assert not e._execute_ron(1)["success"]

    # riichi branches: not your turn, tile not found, success
    e = make_engine()
    tt = e.players[0].hand.concealed_tiles[0]
    assert not e._execute_riichi(1, str(tt))["success"]
    monkeypatch.setattr(e, "_can_declare_riichi", lambda idx: True)
    monkeypatch.setattr(e.players[0], "declare_riichi", lambda turn: None)
    assert not e._execute_riichi(0, "bad")["success"]
    assert e._execute_riichi(0, str(tt))["success"]

    # execute_pass invalid chankan state
    e = make_engine()
    e.pending_chankan_tile = Tile(Suit.MANZU, 1)
    e.pending_chankan_from = None
    e.pending_chankan_responders = {1}
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: False)
    assert not e._execute_pass(1)["success"]

    # execute_pass last discard temp furiten
    e = make_engine()
    e.current_player = 0
    e.last_discard = Tile(Suit.SOUZU, 4)
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: True)
    assert e._execute_pass(1)["success"] and e.players[1].hand.temp_furiten

    # chii invalid sequence length branch
    e = make_engine()
    e.last_discard = Tile(Suit.MANZU, 3)
    e.last_discard_player = 0
    assert not e._execute_chii(1, [str(Tile(Suit.MANZU, 1))])["success"]

    # open kan failure and success with replacement draw
    e = make_engine()
    e.last_discard = Tile(Suit.MANZU, 9)
    e.last_discard_player = 0
    monkeypatch.setattr(e.players[1], "can_call_kan", lambda t: False)
    assert not e._execute_kan(1)["success"]
    monkeypatch.setattr(e.players[1], "can_call_kan", lambda t: True)
    monkeypatch.setattr(e.players[1], "call_kan", lambda tile, who: None)
    monkeypatch.setattr(e.wall, "add_dora_indicator", lambda: None)
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 1)
    monkeypatch.setattr(e.wall, "draw_tile", lambda: Tile(Suit.MANZU, 1))
    assert e._execute_kan(1)["success"] and e.last_action_was_kan_draw

    # _execute_closed_or_added_kan upgrade restriction and cannot declare
    e = make_engine()
    p = e.players[0]
    t = p.hand.concealed_tiles[0]
    monkeypatch.setattr(p, "can_upgrade_pon_to_kan", lambda tile: True)
    monkeypatch.setattr(e, "_riichi_kan_allowed", lambda player, tile: False)
    assert not e._execute_closed_or_added_kan(0, str(t))["success"]
    monkeypatch.setattr(e, "_riichi_kan_allowed", lambda player, tile: True)
    monkeypatch.setattr(e, "_find_chankan_responders", lambda tile, idx: [])
    monkeypatch.setattr(e, "_perform_added_kan", lambda idx, tile: {"success": True})
    assert e._execute_closed_or_added_kan(0, str(t))["success"]

    e = make_engine()
    t2 = e.players[0].hand.concealed_tiles[0]
    e.players[0].hand.concealed_tiles = [t2, t2, t2] + e.players[0].hand.concealed_tiles[3:]
    monkeypatch.setattr(e.players[0], "can_upgrade_pon_to_kan", lambda tile: False)
    assert not e._execute_closed_or_added_kan(0, str(t2))["success"]

    # non-dealer tsumo payments branch
    e = make_engine()
    e.players[0].is_dealer = False
    e.players[1].is_dealer = True
    e._apply_tsumo_payments(0, 0, {"dealer": 200, "non_dealer": 100})

    # advance_turn draws tile path
    e = make_engine()
    e.last_discard = None
    monkeypatch.setattr(e.wall, "tiles_remaining", lambda: 1)
    monkeypatch.setattr(e.wall, "draw_tile", lambda: Tile(Suit.SOUZU, 1))
    e.advance_turn()

    # advance_round east->south and continue
    e = make_engine()
    e.round_wind = Wind.EAST
    e.dealer = 3
    assert e.advance_round() is False and e.round_wind == Wind.SOUTH

    # is_game_over false path
    e = make_engine()
    assert not e.is_game_over()

    # safe/dangerous with tenpai removals/additions
    e = make_engine()
    t = Tile(Suit.MANZU, 1)
    e.players[0].hand.concealed_tiles = [t]
    e.players[1].hand.discards = [t]
    monkeypatch.setattr(e.players[1], "is_tenpai", lambda: True)
    monkeypatch.setattr(e.players[1].hand, "get_winning_tiles", lambda: [t])
    assert e.get_safe_tiles_for_player(0) == []
    assert e.get_dangerous_tiles_for_player(0) == [str(t)]

    # riichi kan restriction false branches
    e = make_engine()
    p = e.players[0]
    kt = Tile(Suit.PINZU, 2)
    p.hand.is_riichi = True
    p.hand.concealed_tiles = [kt, kt, kt]
    assert not e._riichi_kan_allowed(p, kt)
    p.hand.concealed_tiles = [kt, kt, kt, kt]
    monkeypatch.setattr(p.hand, "get_winning_tiles_with_fixed_melds", lambda tiles, fixed_melds=0: [Tile(Suit.MANZU, 1)] if fixed_melds == 0 else [Tile(Suit.MANZU, 2)])
    assert not e._riichi_kan_allowed(p, kt)

def test_cover_remaining_lines(monkeypatch):
    e = make_engine()
    e.pending_chankan_tile = Tile(Suit.MANZU, 1)
    e.pending_chankan_from = 0
    e.pending_chankan_responders = {1, 2}
    monkeypatch.setattr(e.players[1], "can_call_ron", lambda t: False)
    out = e._execute_pass(1)
    assert out["message"] == "Passed chankan"

    e = make_engine()
    for p in e.players:
        p.score = 25000
    e.round_wind = Wind.SOUTH
    e.dealer = 0
    assert e.is_game_over()
