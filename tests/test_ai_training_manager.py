import importlib.util
import json
import sys
import types
from pathlib import Path


def _load_training_manager(monkeypatch):
    class Arr:
        def __init__(self, data):
            self._data = data

        def __len__(self):
            return len(self._data)

        def __getitem__(self, key):
            if isinstance(key, tuple):
                rows, col = key
                data = self._data[rows] if isinstance(rows, slice) else self._data
                return [r[col] for r in data]
            return self._data[key]

    np_mod = types.SimpleNamespace(array=lambda x: Arr(x))

    class Ax:
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

    class Plt:
        def subplots(self, *a, **k):
            return object(), ((Ax(), Ax()), (Ax(), Ax()))

        def tight_layout(self):
            pass

        def savefig(self, path):
            Path(path).write_text("plot")

        def close(self):
            pass

    class Wind:
        EAST = "east"
        SOUTH = "south"
        WEST = "west"
        NORTH = "north"

    monkeypatch.setitem(sys.modules, "numpy", np_mod)
    monkeypatch.setitem(sys.modules, "matplotlib", types.SimpleNamespace(pyplot=Plt()))
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", Plt())
    monkeypatch.setitem(sys.modules, "ai.neural_player", types.SimpleNamespace(NeuralPlayer=object))
    monkeypatch.setitem(sys.modules, "game.engine", types.SimpleNamespace(MahjongEngine=object))
    monkeypatch.setitem(sys.modules, "tiles.tile", types.SimpleNamespace(Wind=Wind))

    spec = importlib.util.spec_from_file_location("tm_under_test", "src/ai/training_manager.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DummyPlayer:
    def __init__(self, name, seat_wind, learning_rate=0.001):
        self.name = name
        self.seat_wind = seat_wind
        self.learning_rate = learning_rate
        self.score = 25000
        self.hand = None
        self.is_dealer = False
        self.rewards = []
        self.results = []

    def load_model(self, path):
        pass

    def save_model(self, path):
        Path(path).write_text("model")

    def choose_action(self, game_state, player_hand, valid_actions):
        return valid_actions[0], {}

    def give_reward(self, reward, next_state=None, done=False):
        self.rewards.append((reward, done))

    def update_game_result(self, won, final_score):
        self.results.append((won, final_score))

    def get_stats(self):
        return {
            "win_rate": 0.25,
            "avg_recent_loss": 0.1,
            "total_games": 1,
            "wins": 0,
            "epsilon": 0.1,
            "memory_size": 1,
            "training_steps": 1,
        }


class DummyGame:
    def __init__(self, names, *, game_ended=False, success=True, no_actions=False):
        self.players = [
            type("P", (), {"score": 25000, "hand": object(), "seat_wind": i, "is_dealer": i == 0})()
            for i, _ in enumerate(names)
        ]
        self.current_player = 0
        self.phase = type("Phase", (), {"value": "play"})()
        self.last_discard = None
        self._game_ended = game_ended
        self._success = success
        self._no_actions = no_actions

    def get_game_state(self):
        return {"x": 1}

    def get_player_hand(self, idx):
        return {"is_tenpai": True}

    def get_valid_actions(self, idx):
        return [] if self._no_actions else ["discard"]

    def execute_action(self, idx, action, **kwargs):
        if self._game_ended:
            self.phase = type("Phase", (), {"value": "ended"})()
            return {"success": self._success, "game_ended": True, "winner": 0}
        return {"success": self._success, "game_ended": False}

    def advance_turn(self):
        self.current_player = (self.current_player + 1) % 4


def test_training_manager_paths(monkeypatch, tmp_path):
    tm = _load_training_manager(monkeypatch)
    monkeypatch.setattr(tm, "NeuralPlayer", DummyPlayer)
    manager = tm.TrainingManager(save_dir=str(tmp_path))

    players = manager.create_neural_players(learning_rate=0.2)
    assert len(players) == 4 and players[0].learning_rate == 0.2

    monkeypatch.setattr(tm, "MahjongEngine", lambda names: DummyGame(names, game_ended=True))
    manager.train_players(num_games=1, save_interval=1, learning_rate=0.3)
    assert players[0].hand is None  # independent from trainer-owned players

    out = manager.play_training_game(DummyGame([p.name for p in manager.create_neural_players()], game_ended=True), manager.create_neural_players())
    assert out["winner"] == 0

    no_action_players = manager.create_neural_players()
    manager.play_training_game(DummyGame([p.name for p in no_action_players], no_actions=True), no_action_players)
    assert no_action_players[0].rewards[-1][0] == -1.0

    bad_players = manager.create_neural_players()
    manager.play_training_game(DummyGame([p.name for p in bad_players], game_ended=True, success=False), bad_players)
    assert bad_players[0].rewards[-1][0] == -1.0

    assert manager.calculate_action_reward("ron", {}, {}) == 20.0
    assert manager.calculate_action_reward("riichi", {}, {}) == 2.0
    assert manager.calculate_action_reward("discard", {}, {"is_tenpai": True}) == 0.5
    assert manager.calculate_action_reward("discard", {}, {}) == 0.1
    assert manager.calculate_action_reward("pon", {}, {}) == 1.0
    assert manager.calculate_action_reward("pass", {}, {}) == 0.1

    ps = manager.create_neural_players()
    manager.update_training_stats(ps, {"winner": 0})
    manager.save_training_stats()
    payload = json.loads((tmp_path / "training_stats.json").read_text())
    assert payload["games_played"] >= 1

    manager.plot_training_progress()
    for _ in range(10):
        manager.training_stats["win_rates"].append([0.2, 0.2, 0.2, 0.2])
        manager.training_stats["avg_scores"].append([25000] * 4)
        manager.training_stats["training_losses"].append([0.1] * 4)
    manager.plot_training_progress()
    assert (tmp_path / "training_progress.png").exists()

    manager.print_final_stats(ps)
    monkeypatch.setattr(tm, "MahjongEngine", lambda names: DummyGame(names, game_ended=True))
    assert manager.evaluate_players(1)["total_games"] == 1
    assert manager.calculate_eval_stats([], ps)["total_games"] == 0


class EndlessGame(DummyGame):
    def __init__(self, names):
        super().__init__(names, game_ended=False, success=True, no_actions=False)
        self.last_discard = object()

    def execute_action(self, idx, action, **kwargs):
        return {"success": True, "game_ended": False}


def test_training_manager_remaining_branches(monkeypatch, tmp_path):
    tm = _load_training_manager(monkeypatch)
    monkeypatch.setattr(tm, "NeuralPlayer", DummyPlayer)
    manager = tm.TrainingManager(save_dir=str(tmp_path))
    # Cover model loading branch
    for i in range(1, 5):
        (tmp_path / f"player_{i}_model.pth").write_text("x")

    monkeypatch.setattr(tm, "MahjongEngine", lambda names: DummyGame(names, game_ended=True))
    manager.train_players(num_games=1, save_interval=1, learning_rate=0.1)

    # Cover max-turn draw path
    players = manager.create_neural_players()
    result = manager.play_training_game(EndlessGame([p.name for p in players]), players)
    assert result["game_ended_normally"] is False

    # Cover evaluate progress print branch
    stats = manager.evaluate_players(10)
    assert stats["total_games"] == 10


class AdvanceTurnGame(DummyGame):
    def __init__(self, names):
        super().__init__(names, game_ended=False, success=True, no_actions=False)
        self.calls = 0

    def get_valid_actions(self, idx):
        self.calls += 1
        return ["discard"] if self.calls == 1 else []


def test_training_manager_advance_turn_branch(monkeypatch, tmp_path):
    tm = _load_training_manager(monkeypatch)
    monkeypatch.setattr(tm, "NeuralPlayer", DummyPlayer)
    m = tm.TrainingManager(save_dir=str(tmp_path))
    players = m.create_neural_players()
    game = AdvanceTurnGame([p.name for p in players])
    m.play_training_game(game, players)
    assert game.current_player == 1
