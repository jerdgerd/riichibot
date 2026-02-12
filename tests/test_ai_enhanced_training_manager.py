import importlib.util
import sys
import types
from pathlib import Path


def _load_modules(monkeypatch):
    spec = importlib.util.spec_from_file_location("ai_config_under_test", "src/ai/config.py")
    config_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_mod)

    class Wind:
        EAST = "east"
        SOUTH = "south"
        WEST = "west"
        NORTH = "north"

    monkeypatch.setitem(sys.modules, "ai.config", config_mod)
    monkeypatch.setitem(sys.modules, "ai.logger", types.SimpleNamespace(TrainingLogger=object))
    monkeypatch.setitem(sys.modules, "ai.metrics", types.SimpleNamespace(PerformanceAnalyzer=object))
    monkeypatch.setitem(sys.modules, "ai.neural_player", types.SimpleNamespace(NeuralPlayer=object))
    monkeypatch.setitem(sys.modules, "game.engine", types.SimpleNamespace(MahjongEngine=object))
    monkeypatch.setitem(sys.modules, "tiles.tile", types.SimpleNamespace(Wind=Wind))

    spec2 = importlib.util.spec_from_file_location(
        "enhanced_tm_under_test", "src/ai/enhanced_training_manager.py"
    )
    mod = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(mod)
    return mod, config_mod.TrainingConfig


class DummyMemory(list):
    def __init__(self, maxlen=None):
        super().__init__()
        self.maxlen = maxlen


class DummyPlayer:
    def __init__(self, name, seat_wind, learning_rate=0.001):
        self.name = name
        self.seat_wind = seat_wind
        self.learning_rate = learning_rate
        self.batch_size = 0
        self.memory = DummyMemory(maxlen=1)
        self.epsilon = 0.5
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.9
        self.target_update_freq = 1
        self.score = 25000
        self.hand = type("H", (), {"concealed_tiles": []})()
        self.is_dealer = False
        self.total_games = 0
        self.wins = 0
        self.rewards = []

    def choose_action(self, game_state, player_hand, valid_actions):
        return valid_actions[0], {}

    def give_reward(self, reward, next_state=None, done=False):
        self.rewards.append((reward, done))

    def update_game_result(self, won, final_score):
        self.rewards.append((99.0, True))

    def get_stats(self):
        return {
            "win_rate": 0.5,
            "epsilon": self.epsilon,
            "memory_size": len(self.memory),
            "avg_recent_loss": 0.1,
        }

    def save_model(self, path):
        Path(path).write_text("x")

    def load_model(self, path):
        pass


class DummyLogger:
    def __init__(self, *args, **kwargs):
        self.logger = type("L", (), {"info": lambda self, _: None})()

    def log_game_result(self, *a, **k):
        pass

    def save_stats(self):
        pass

    def log_training_milestone(self, *a, **k):
        pass

    def log_evaluation_results(self, *a, **k):
        pass


class DummyAnalyzer:
    def add_game_result(self, *a, **k):
        pass

    def plot_learning_curves(self, save_path):
        Path(save_path).write_text("plot")

    def generate_report(self):
        return "ok"


class DummyGame:
    def __init__(self, names, *, ended=False, no_actions=False):
        self.players = [
            type("P", (), {"score": 25000, "hand": type("H", (), {"concealed_tiles": []})(), "seat_wind": i, "is_dealer": i == 0})()
            for i, _ in enumerate(names)
        ]
        self.current_player = 0
        self.phase = type("Phase", (), {"value": "play"})()
        self.last_discard = None
        self._ended = ended
        self._no_actions = no_actions
        self.wall = type("W", (), {"tiles_remaining": lambda self: 7})()

    def get_game_state(self):
        return {"dummy": 1}

    def get_player_hand(self, idx):
        return {"winning_tiles": [1], "is_tenpai": True, "concealed_tiles": []}

    def get_valid_actions(self, idx):
        return [] if self._no_actions else ["discard", "pass"]

    def execute_action(self, idx, action, **kwargs):
        if self._ended:
            self.phase = type("Phase", (), {"value": "ended"})()
            return {
                "success": True,
                "game_ended": True,
                "winner": 0,
                "yaku": [{"name": "riichi"}, {"name": "pinfu"}],
                "score": 5200,
                "final_scores": [30000, 25000, 23000, 22000],
            }
        return {"success": False, "game_ended": False, "message": "bad"}

    def advance_turn(self):
        self.current_player = (self.current_player + 1) % 4


def test_enhanced_training_manager_logic(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)

    cfg = TrainingConfig(num_games=1, save_interval=1, eval_interval=1, eval_games=1)
    manager = etm.EnhancedTrainingManager(cfg, save_dir=str(tmp_path), experiment_name="x")
    players = manager.create_neural_players()
    assert players[0].memory.maxlen == cfg.memory_size

    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DummyGame(names, ended=True))
    result = manager.play_training_game(players)
    assert result["winner"] == 0
    assert players[0].wins == 1 and players[0].total_games == 1

    assert manager.calculate_enhanced_reward("tsumo", {}, {}, {}) == cfg.win_reward
    assert manager.calculate_enhanced_reward("riichi", {}, {"winning_tiles": [1, 2]}, {}) > cfg.riichi_reward
    assert manager.calculate_enhanced_reward("discard", {}, {"is_tenpai": True, "winning_tiles": [1], "concealed_tiles": []}, {}) > 0
    assert manager.calculate_enhanced_reward("discard", {}, {"winning_tiles": [1], "concealed_tiles": []}, {}) > 0
    assert manager.calculate_enhanced_reward("discard", {}, {"winning_tiles": [], "concealed_tiles": []}, {}) < 0
    assert manager.calculate_enhanced_reward("pon", {}, {"winning_tiles": [1]}, {}) > 0
    assert manager.calculate_enhanced_reward("pon", {}, {"winning_tiles": []}, {}) > 0
    assert manager.calculate_enhanced_reward("pass", {}, {}, {}) > 0
    assert manager.calculate_enhanced_reward("other", {}, {}, {}) > 0

    assert manager.calculate_final_reward(True, 30000, {"score": 5200, "yaku": [{"name": "riichi"}, {"name": "pinfu"}]}) > cfg.win_reward
    assert manager.calculate_final_reward(False, 26000, {"winner": -1, "tenpai_players": [2], "player_index": 2}) == 2.0
    assert manager.calculate_final_reward(False, 24000, {"winner": 1, "final_scores": [30000, 26000, 24000, 20000]}) < 0
    assert manager._calculate_position(123, []) == 4

    prior = len(players[0].rewards)
    manager.give_progress_reward(players[0], {"winning_tiles": [], "is_tenpai": False}, {"winning_tiles": [1], "is_tenpai": True})
    manager.give_progress_reward(players[0], {"winning_tiles": [1], "is_tenpai": False}, {"winning_tiles": [2, 3], "is_tenpai": False})
    manager.give_progress_reward(players[0], {"winning_tiles": [2, 3], "is_tenpai": False}, {"winning_tiles": [1], "is_tenpai": False})
    assert len(players[0].rewards) > prior

    assert "player_1" in manager.get_milestone_stats(players)
    manager.save_all_models(players)
    assert (tmp_path / "player_1_model.pth").exists()
    assert manager.evaluate_players(players)["total_games"] == 1

    manager.train_players()
    assert (tmp_path / "final_training_report.txt").exists()


def test_enhanced_training_manager_edge_paths(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DummyGame(names, no_actions=True))

    manager = etm.EnhancedTrainingManager(
        TrainingConfig(num_games=1, save_interval=1, eval_interval=1, eval_games=0),
        save_dir=str(tmp_path),
        experiment_name="x",
    )
    players = manager.create_neural_players()
    assert manager.play_training_game(players)["winner"] == -1
    assert manager.evaluate_players(players)["total_games"] == 0
    game = DummyGame(["a", "b", "c", "d"]) 
    game.last_discard = object()
    assert manager._should_advance_turn(game, "discard") is False


class CallOnlyGame(DummyGame):
    def get_valid_actions(self, idx):
        return ["chii"]

    def execute_action(self, idx, action, **kwargs):
        return {"success": True, "game_ended": False, "message": "ok"}


class InvalidActionGame(DummyGame):
    def execute_action(self, idx, action, **kwargs):
        return {"success": False, "game_ended": False, "message": "nope"}


def test_enhanced_manager_additional_branches(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)

    # hit game % 50 logger branch and model load branch
    cfg = TrainingConfig(num_games=50, save_interval=25, eval_interval=25, eval_games=0)
    manager = etm.EnhancedTrainingManager(cfg, save_dir=str(tmp_path), experiment_name="x")
    for i in range(1, 5):
        (tmp_path / f"player_{i}_model.pth").write_text("x")

    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DummyGame(names, ended=True))
    manager.train_players()

    # hit invalid action branch
    players = manager.create_neural_players()
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: InvalidActionGame(names, ended=False))
    manager.play_training_game(players)

    # hit call-action and max-turn draw/update_game_result branch
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: CallOnlyGame(names, ended=False))
    out = manager.play_training_game(manager.create_neural_players())
    assert out["game_ended_normally"] is False

    # _should_advance_turn true path
    game = DummyGame(["a", "b", "c", "d"]) 
    game.last_discard = object()
    game.get_valid_actions = lambda idx: ["pass"]
    assert manager._should_advance_turn(game, "discard") is True

    # draw-neutral branch in final reward
    assert manager.calculate_final_reward(False, 25000, {"winner": -1, "tenpai_players": [], "player_index": 3}) == 0.0


class DiscardAdvanceGame(DummyGame):
    def __init__(self, names):
        super().__init__(names, ended=False, no_actions=False)
        self.last_discard = object()
        self.calls = 0

    def get_valid_actions(self, idx):
        return ["pass"]

    def execute_action(self, idx, action, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {"success": True, "game_ended": False, "message": "ok"}
        return {"success": False, "game_ended": False, "message": "stop"}


class PassGame(DummyGame):
    def get_valid_actions(self, idx):
        return ["pass"]

    def execute_action(self, idx, action, **kwargs):
        return {"success": False, "game_ended": False, "message": "x"}


def test_enhanced_manager_turn_flow_branches(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)

    manager = etm.EnhancedTrainingManager(TrainingConfig(num_games=1, eval_games=0), save_dir=str(tmp_path), experiment_name="x")

    players = manager.create_neural_players()
    players[0].choose_action = lambda s, h, v: ("discard", {})
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DiscardAdvanceGame(names))
    manager.play_training_game(players)

    players2 = manager.create_neural_players()
    players2[0].choose_action = lambda s, h, v: ("pass", {})
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: PassGame(names))
    manager.play_training_game(players2)

class ResponderActionGame(DummyGame):
    def __init__(self, names):
        super().__init__(names, ended=False, no_actions=False)
        self.last_discard = object()
        self.step = 0

    def get_valid_actions(self, idx):
        if self.step == 0 and idx == 0:
            return ["discard"]
        if idx == 1:
            return []  # cover responder continue branch
        if idx == 2:
            return ["pon"]
        return ["pass"]

    def execute_action(self, idx, action, **kwargs):
        self.step += 1
        if self.step == 1:
            return {"success": True, "game_ended": False, "message": "discarded"}
        # responder action succeeds and ends game
        return {
            "success": True,
            "game_ended": True,
            "winner": idx,
            "message": "won",
            "yaku": [{"name": "riichi"}],
            "score": 3900,
            "final_scores": [24000, 24000, 28000, 24000],
        }


def test_enhanced_manager_responder_branches(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: ResponderActionGame(names))

    manager = etm.EnhancedTrainingManager(
        TrainingConfig(num_games=1, eval_games=0),
        save_dir=str(tmp_path),
        experiment_name="x",
    )

    players = manager.create_neural_players()
    players[0].choose_action = lambda s, h, v: ("discard", {})
    players[2].choose_action = lambda s, h, v: ("pon", {})

    out = manager.play_training_game(players)

    assert out["winner"] == 2
    assert out["game_ended_normally"] is True
    assert any(done for _, done in players[2].rewards)

class ResponderCallNoEndGame(DummyGame):
    def __init__(self, names):
        super().__init__(names, ended=False, no_actions=False)
        self.last_discard = object()
        self.step = 0

    def get_valid_actions(self, idx):
        if idx == 0:
            return ["discard"]
        if idx == 1:
            return ["pon"]
        return ["pass"]

    def execute_action(self, idx, action, **kwargs):
        self.step += 1
        if self.step == 1:
            return {"success": True, "game_ended": False, "message": "discarded"}
        return {"success": True, "game_ended": False, "message": "called"}


def test_enhanced_manager_call_was_made_branch_and_default_should_advance(monkeypatch, tmp_path):
    etm, TrainingConfig = _load_modules(monkeypatch)
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: ResponderCallNoEndGame(names))

    manager = etm.EnhancedTrainingManager(
        TrainingConfig(num_games=1, eval_games=0),
        save_dir=str(tmp_path),
        experiment_name="x",
    )

    players = manager.create_neural_players()
    players[0].choose_action = lambda s, h, v: ("discard", {})
    players[1].choose_action = lambda s, h, v: ("pon", {})

    out = manager.play_training_game(players)
    assert out["game_ended_normally"] is False

    game = DummyGame(["a", "b", "c", "d"])
    assert manager._should_advance_turn(game, "pass") is False
