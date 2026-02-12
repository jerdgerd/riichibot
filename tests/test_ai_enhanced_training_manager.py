import importlib.util
import sys
import types
from pathlib import Path


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


config_mod = load_module("config_mod", "src/ai/config.py")
sys.modules["ai.config"] = config_mod
sys.modules["ai.logger"] = types.SimpleNamespace(TrainingLogger=object)
sys.modules["ai.metrics"] = types.SimpleNamespace(PerformanceAnalyzer=object)
sys.modules["ai.neural_player"] = types.SimpleNamespace(NeuralPlayer=object)
sys.modules["game.engine"] = types.SimpleNamespace(MahjongEngine=object)


class Wind:
    EAST = "east"
    SOUTH = "south"
    WEST = "west"
    NORTH = "north"


sys.modules["tiles.tile"] = types.SimpleNamespace(Wind=Wind)
etm = load_module("etm", "src/ai/enhanced_training_manager.py")
TrainingConfig = config_mod.TrainingConfig


class DummyMemory(list):
    def __init__(self, maxlen=None):
        super().__init__()
        self.maxlen = maxlen


class DummyPlayer:
    def __init__(self, name, seat_wind, learning_rate=0.001):
        self.name = name
        self.batch_size = 0
        self.memory = DummyMemory(maxlen=1)
        self.epsilon = 0.5
        self.epsilon_min = 0.1
        self.epsilon_decay = 0.9
        self.target_update_freq = 1
        self.score = 25000
        self.hand = type("H", (), {"concealed_tiles": []})()
        self.total_games = 0
        self.wins = 0
        self.seat_wind = seat_wind
        self.is_dealer = False

    def choose_action(self, game_state, player_hand, valid_actions):
        return valid_actions[0], {}

    def give_reward(self, reward, next_state=None, done=False):
        pass

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
        self.logger = type("L", (), {"info": lambda self, x: None})()

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
    def __init__(self, names, no_actions=False, game_ended=False):
        self.players = [type("P", (), {"score": 25000, "hand": type("H", (), {"concealed_tiles": []})(), "seat_wind": None, "is_dealer": False})() for _ in names]
        self.current_player = 0
        self.phase = type("Phase", (), {"value": "play"})()
        self.last_discard = None
        self.no_actions = no_actions
        self.game_ended = game_ended
        self.wall = type("W", (), {"tiles_remaining": lambda self: 1})()

    def get_game_state(self):
        return {"dummy": 1}

    def get_player_hand(self, idx):
        return {"winning_tiles": [1], "is_tenpai": True, "concealed_tiles": []}

    def get_valid_actions(self, idx):
        return [] if self.no_actions else ["discard", "pass"]

    def execute_action(self, idx, action, **kwargs):
        if self.game_ended:
            self.phase = type("Phase", (), {"value": "ended"})()
            return {"success": True, "game_ended": True, "winner": 0, "yaku": [{"name": "riichi"}], "score": 3900}
        return {"success": False, "game_ended": False, "message": "bad"}

    def advance_turn(self):
        self.current_player = (self.current_player + 1) % 4


def test_enhanced_training_manager(monkeypatch, tmp_path):
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)

    config = TrainingConfig(num_games=1, save_interval=1, eval_interval=1, eval_games=1)
    manager = etm.EnhancedTrainingManager(config, save_dir=str(tmp_path), experiment_name="x")
    players = manager.create_neural_players()

    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DummyGame(names, game_ended=True))
    result = manager.play_training_game(players)
    assert result["winner"] == 0
    assert players[0].wins == 1

    manager.train_players()
    assert (tmp_path / "final_training_report.txt").exists()

    assert manager.calculate_enhanced_reward("pass", {}, {}, {}) > 0
    assert manager.calculate_final_reward(False, 25000, {"winner": -1, "tenpai_players": [2], "player_index": 2}) == 2.0
    assert manager._calculate_position(123, []) == 4

    stats = manager.evaluate_players(players)
    assert stats["total_games"] == 1


def test_enhanced_training_manager_edges(monkeypatch, tmp_path):
    monkeypatch.setattr(etm, "NeuralPlayer", DummyPlayer)
    monkeypatch.setattr(etm, "TrainingLogger", DummyLogger)
    monkeypatch.setattr(etm, "PerformanceAnalyzer", DummyAnalyzer)
    monkeypatch.setattr(etm, "MahjongEngine", lambda names: DummyGame(names, no_actions=True))

    manager = etm.EnhancedTrainingManager(TrainingConfig(num_games=1, eval_games=0), save_dir=str(tmp_path), experiment_name="x")
    players = manager.create_neural_players()
    assert manager.play_training_game(players)["winner"] == -1
    assert manager.evaluate_players(players)["total_games"] == 0
