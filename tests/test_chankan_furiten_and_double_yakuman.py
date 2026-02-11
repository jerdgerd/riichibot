from src.game.engine import MahjongEngine
from src.game.hand import Hand
from src.game.rules import YakuChecker
from src.game.scoring import Scoring
from tiles.tile import Dragon, Suit, Tile, Wind


def _simple_tenpai_waiting_on(tile: Tile):
    # Chiitoitsu 6 pairs + single wait tile.
    return [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.MANZU, 2),
        Tile(Suit.PINZU, 4),
        Tile(Suit.PINZU, 4),
        Tile(Suit.PINZU, 5),
        Tile(Suit.PINZU, 5),
        Tile(Suit.SOUZU, 6),
        Tile(Suit.SOUZU, 6),
        Tile(Suit.SOUZU, 7),
        Tile(Suit.SOUZU, 7),
        tile,
    ]


def test_furiten_only_checks_own_discards():
    hand = Hand()
    winning_tile = Tile(Suit.SOUZU, 4)
    hand.concealed_tiles = _simple_tenpai_waiting_on(winning_tile)

    assert not hand.check_furiten([[], [winning_tile], [], []])

    hand.discards.append(winning_tile)
    assert hand.check_furiten([[], [], [], []])


def test_pass_sets_temp_furiten_until_next_draw():
    engine = MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)
    p1 = engine.players[1]
    winning_tile = Tile(Suit.SOUZU, 4)
    p1.hand.concealed_tiles = _simple_tenpai_waiting_on(winning_tile)

    engine.current_player = 0
    engine.last_discard = winning_tile
    engine.last_discard_player = 0

    assert p1.can_call_ron(winning_tile)
    result = engine.execute_action(1, "pass")
    assert result["success"]
    assert p1.hand.temp_furiten
    assert not p1.can_call_ron(winning_tile)

    p1.draw_tile(Tile(Suit.MANZU, 9))
    assert not p1.hand.temp_furiten


def test_added_kan_chankan_flow():
    engine = MahjongEngine(["A", "B", "C", "D"], use_red_fives=False)
    kan_player = engine.players[0]
    robber = engine.players[1]

    kan_tile = Tile(Suit.MANZU, 3)
    kan_player.hand.concealed_tiles = [
        kan_tile,
        kan_tile,
        kan_tile,
        Tile(Suit.PINZU, 1),
        Tile(Suit.PINZU, 2),
        Tile(Suit.PINZU, 3),
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 2),
        Tile(Suit.SOUZU, 3),
        Tile(Suit.MANZU, 5),
        Tile(Suit.MANZU, 6),
        Tile(Suit.MANZU, 7),
        Tile(Suit.WIND, wind=Wind.EAST),
    ]
    kan_player.call_pon(kan_tile, called_from=2)

    robber.hand.concealed_tiles = _simple_tenpai_waiting_on(kan_tile)

    engine.current_player = 0
    engine.last_discard = None

    start_kan_score = kan_player.score
    start_robber_score = robber.score

    declare = engine.execute_action(0, "kan", tile=str(kan_tile))
    assert declare["success"]
    assert declare.get("pending_chankan")
    assert "ron" in engine.get_valid_actions(1)

    ron = engine.execute_action(1, "ron")
    assert ron["success"]
    assert ron["game_ended"]
    yaku_names = {item["name"] for item in ron["yaku"]}
    assert "Chankan" in yaku_names
    assert kan_player.score < start_kan_score
    assert robber.score > start_robber_score


def test_double_yakuman_variants_detected_and_scored():
    # Kokushi 13-wait
    kokushi_hand = Hand()
    kokushi_hand.concealed_tiles = [
        Tile(Suit.SOUZU, 1),
        Tile(Suit.SOUZU, 9),
        Tile(Suit.PINZU, 1),
        Tile(Suit.PINZU, 9),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 9),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.SOUTH),
        Tile(Suit.WIND, wind=Wind.WEST),
        Tile(Suit.WIND, wind=Wind.NORTH),
        Tile(Suit.DRAGON, dragon=Dragon.WHITE),
        Tile(Suit.DRAGON, dragon=Dragon.GREEN),
        Tile(Suit.DRAGON, dragon=Dragon.RED),
    ]
    kokushi_win = Tile(Suit.SOUZU, 1)
    kokushi_yaku = YakuChecker.check_all_yaku(
        kokushi_hand,
        kokushi_win,
        False,
        Wind.EAST,
        Wind.EAST,
        dora_tiles=[],
    )
    kokushi_map = {item.name: item.han for item in kokushi_yaku}
    assert kokushi_map.get("Kokushi Musou 13-Wait") == 26

    # Suuankou tanki
    suuankou_hand = Hand()
    suuankou_hand.concealed_tiles = [
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
        Tile(Suit.MANZU, 4),
        Tile(Suit.PINZU, 5),
    ]
    tanki_win = Tile(Suit.PINZU, 5)
    suuankou_yaku = YakuChecker.check_all_yaku(
        suuankou_hand,
        tanki_win,
        False,
        Wind.EAST,
        Wind.EAST,
        dora_tiles=[],
    )
    suuankou_map = {item.name: item.han for item in suuankou_yaku}
    assert suuankou_map.get("Suuankou Tanki") == 26

    # Junsei Chuuren
    chuuren_hand = Hand()
    chuuren_hand.concealed_tiles = [
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 1),
        Tile(Suit.MANZU, 2),
        Tile(Suit.MANZU, 3),
        Tile(Suit.MANZU, 4),
        Tile(Suit.MANZU, 5),
        Tile(Suit.MANZU, 6),
        Tile(Suit.MANZU, 7),
        Tile(Suit.MANZU, 8),
        Tile(Suit.MANZU, 9),
        Tile(Suit.MANZU, 9),
        Tile(Suit.MANZU, 9),
    ]
    chuuren_win = Tile(Suit.MANZU, 5)
    chuuren_yaku = YakuChecker.check_all_yaku(
        chuuren_hand,
        chuuren_win,
        True,
        Wind.EAST,
        Wind.EAST,
        dora_tiles=[],
    )
    chuuren_map = {item.name: item.han for item in chuuren_yaku}
    assert chuuren_map.get("Junsei Chuuren Poutou") == 26

    # Daisuushii is treated as double yakuman.
    daisuushii_hand = Hand()
    daisuushii_hand.concealed_tiles = [
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.EAST),
        Tile(Suit.WIND, wind=Wind.SOUTH),
        Tile(Suit.WIND, wind=Wind.SOUTH),
        Tile(Suit.WIND, wind=Wind.SOUTH),
        Tile(Suit.WIND, wind=Wind.WEST),
        Tile(Suit.WIND, wind=Wind.WEST),
        Tile(Suit.WIND, wind=Wind.WEST),
        Tile(Suit.WIND, wind=Wind.NORTH),
        Tile(Suit.WIND, wind=Wind.NORTH),
        Tile(Suit.WIND, wind=Wind.NORTH),
        Tile(Suit.MANZU, 5),
    ]
    daisuushii_win = Tile(Suit.MANZU, 5)
    daisuushii_yaku = YakuChecker.check_all_yaku(
        daisuushii_hand,
        daisuushii_win,
        True,
        Wind.EAST,
        Wind.EAST,
        dora_tiles=[],
    )
    daisuushii_map = {item.name: item.han for item in daisuushii_yaku}
    assert daisuushii_map.get("Daisuushii") == 26

    # Validate scoring conversion from 26-han yakuman.
    daisuushii_only = [item for item in daisuushii_yaku if item.name == "Daisuushii"]
    score, payments = Scoring.calculate_score(
        yaku_list=daisuushii_only,
        is_dealer=False,
        is_tsumo=False,
    )
    assert score == 64000
    assert payments == {"discarder": 64000}
