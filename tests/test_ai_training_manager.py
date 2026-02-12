import importlib.util
import json
import sys
import types
from pathlib import Path


def load_training_manager_module():
    class ArrayWrap:
        def __init__(self, data):
            self.data = data

        def __len__(self):
            return len(self.data)

        def __getitem__(self, key):
            if isinstance(key, tuple):
                rows, col = key
                subset = self.data[rows] if not isinstance(rows, slice) else self.data[rows]
                return [r[col] for r in subset]
            return self.data[key]

    np_mod = types.SimpleNamespace(array=lambda x: ArrayWrap(x))

    class DummyAx:
        def plot(self, *a, **k):
            pass

        def set_title(self, *a, **k):
            pass

        def set_xlabel(self, *a, **k):
            pass

        def set_ylabel(self, *a, **k):
            pass

        def legend(self, *a, **k):
            pass

        def grid(self, *a, **k):
            pass

        def boxplot(self, *a, **k):
            pass

    class DummyPlt(types.SimpleNamespace):
        def subplots(self, *a, **k):
            return object(), ((DummyAx(), DummyAx()), (DummyAx(), DummyAx()))

        def tight_layout(self):
            pass

        def savefig(self, path):
            Path(path).write_text("plot")

        def close(self):
            pass

    matplotlib_mod = types.SimpleNamespace(pyplot=DummyPlt())

    class Wind:
        EAST = "east"
        SOUTH = "south"
        WEST = "west"
        NORTH = "north"

    sys.modules["numpy"] = np_mod
    sys.modules["matplotlib"] = matplotlib_mod
    sys.modules["matplotlib.pyplot"] = matplotlib_mod.pyplot
    sys.modules["ai.neural_player"] = types.SimpleNamespace(NeuralPlayer=object)
    sys.modules["game.engine"] = types.SimpleNamespace(MahjongEngine=object)
    sys.modules["tiles.tile"] = types.SimpleNamespace(Wind=Wind)

    spec = importlib.util.spec_from_file_location("tm", "src/ai/training_manager.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tm = load_training_manager_module()


class DummyPlayer:
    def __init__(self, name, seat_wind, learning_rate=0.001):
        self.name = name
        self.seat_wind = seat_wind
        self.learning_rate = learning_rate
        self.score = 25000
        self.rewards = []
        self.results = []

    def load_model(self, path):
        pass

    def save_model(self, path):
        Path(path).write_text("m")

    def choose_action(self, game_state, player_hand, valid_actions):
        return valid_actions[0], {}

    def give_reward(self, reward, next_state=None, done=False):
        self.rewards.append((reward, done))

    def update_game_result(self, won, final_score):
        self.results.append((won, final_score))

    def get_stats(self):
        return {
            "win_rate": 0.25,
            "avg_recent_loss": 0.2,
            "total_games": 1,
            "wins": 0,
            "epsilon": 0.1,
            "memory_size": 1,
            "training_steps": 1,
        }


class DummyGame:
    def __init__(self, names, end_immediately=False, game_ended=False, success=True):
        self.players = [type("P", (), {"score": 25000})() for _ in names]
        self.current_player = 0
        self.phase = type("Phase", (), {"value": "play" if not end_immediately else "ended"})()
        self.last_discard = None
        self._game_ended = game_ended
        self._success = success

    def get_game_state(self):
        return {"dummy": 1}

    def get_player_hand(self, idx):
        return {"is_tenpai": True}

    def get_valid_actions(self, idx):
        return ["discard"]

    def execute_action(self, idx, action, **kwargs):
        if self._game_ended:
            self.phase = type("Phase", (), {"value": "ended"})()
            return {"success": self._success, "game_ended": True, "winner": 0}
        return {"success": self._success, "game_ended": False}

    def advance_turn(self):
        self.current_player = (self.current_player + 1) % 4


def test_training_manager_end_to_end(monkeypatch, tmp_path):
    monkeypatch.setattr(tm, "NeuralPlayer", DummyPlayer)
    manager = tm.TrainingManager(save_dir=str(tmp_path))

    players = manager.create_neural_players(learning_rate=0.5)
    assert players[0].learning_rate == 0.5

    monkeypatch.setattr(tm, "MahjongEngine", lambda names: DummyGame(names, game_ended=True))
    manager.train_players(num_games=1, save_interval=1, learning_rate=0.7)
    assert (tmp_path / "training_stats.json").exists()

    result = manager.play_training_game(DummyGame([p.name for p in players], game_ended=True), players)
    assert result["winner"] == 0

    draw = manager.play_training_game(DummyGame([p.name for p in players]), players)
    assert draw["game_ended_normally"] is False

    bad = DummyGame([p.name for p in players], game_ended=True, success=False)
    manager.play_training_game(bad, players)
    assert players[0].rewards[-1][0] == -1.0

    assert manager.calculate_action_reward("pass", {}, {}) == 0.1
    manager.update_training_stats(players, result)
    manager.save_training_stats()
    payload = json.loads((tmp_path / "training_stats.json").read_text())
    assert payload["games_played"] >= 1

    for _ in range(10):
        manager.training_stats["win_rates"].append([0.1, 0.2, 0.3, 0.4])
        manager.training_stats["avg_scores"].append([1, 2, 3, 4])
        manager.training_stats["training_losses"].append([0.1, 0.2, 0.3, 0.4])
    manager.plot_training_progress()
    assert (tmp_path / "training_progress.png").exists()

    manager.print_final_stats(players)

    stats = manager.evaluate_players(num_eval_games=1)
    assert stats["total_games"] == 1
    assert manager.calculate_eval_stats([], players)["total_games"] == 0
