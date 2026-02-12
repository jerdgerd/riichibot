import importlib.util
import sys
import types


class DummyTrainer:
    def __init__(self, save_dir):
        self.save_dir = save_dir
        self.calls = []

    def train_players(self, **kwargs):
        self.calls.append(("train", kwargs))

    def evaluate_players(self, n):
        self.calls.append(("eval", n))


def load_train_module(factory):
    sys.modules["ai.training_manager"] = types.SimpleNamespace(TrainingManager=factory)
    spec = importlib.util.spec_from_file_location("train_ai", "src/ai/train_ai.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_train_cli_train_and_eval(monkeypatch):
    holder = {}

    def factory(save_dir):
        holder["trainer"] = DummyTrainer(save_dir)
        return holder["trainer"]

    train_ai = load_train_module(factory)
    monkeypatch.setattr(
        sys,
        "argv",
        ["train_ai.py", "--games", "2", "--save-interval", "1", "--learning-rate", "0.2", "--save-dir", "m", "--eval-games", "3"],
    )
    train_ai.main()
    trainer = holder["trainer"]
    assert trainer.calls[0][1]["learning_rate"] == 0.2
    assert trainer.calls[1] == ("eval", 3)


def test_train_cli_eval_only(monkeypatch):
    holder = {}

    def factory(save_dir):
        holder["trainer"] = DummyTrainer(save_dir)
        return holder["trainer"]

    train_ai = load_train_module(factory)
    monkeypatch.setattr(sys, "argv", ["train_ai.py", "--eval-only", "--eval-games", "4"])
    train_ai.main()
    assert holder["trainer"].calls == [("eval", 4)]



def test_train_cli_main_module_entry(monkeypatch):
    import runpy

    holder = {}

    def factory(save_dir):
        holder["trainer"] = DummyTrainer(save_dir)
        return holder["trainer"]

    monkeypatch.setitem(sys.modules, "ai.training_manager", types.SimpleNamespace(TrainingManager=factory))
    monkeypatch.setattr(sys, "argv", ["train_ai.py", "--eval-only", "--eval-games", "1"])
    runpy.run_path("src/ai/train_ai.py", run_name="__main__")
    assert holder["trainer"].calls == [("eval", 1)]
