import importlib.util
import sys
import types


def _load_neural_player_module(monkeypatch):
    dummy_nn = types.SimpleNamespace(
        Module=object,
        Linear=lambda *a, **k: None,
        ReLU=lambda *a, **k: None,
        Dropout=lambda *a, **k: None,
        Sequential=lambda *a, **k: None,
        MSELoss=lambda *a, **k: None,
    )
    dummy_torch = types.ModuleType("torch")
    dummy_torch.cuda = types.SimpleNamespace(is_available=lambda: False)
    dummy_torch.device = lambda _: "cpu"
    dummy_torch.FloatTensor = lambda x: x
    dummy_torch.no_grad = types.SimpleNamespace
    dummy_torch.tensor = lambda *a, **k: 0
    dummy_torch.stack = lambda x: x
    dummy_torch.BoolTensor = lambda x: x
    dummy_torch.Tensor = object
    dummy_torch.nn = dummy_nn
    dummy_optim = types.SimpleNamespace(Adam=lambda *a, **k: None)

    monkeypatch.setitem(sys.modules, "numpy", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "torch", dummy_torch)
    monkeypatch.setitem(sys.modules, "torch.nn", dummy_nn)
    monkeypatch.setitem(sys.modules, "torch.optim", dummy_optim)
    monkeypatch.setitem(sys.modules, "game.engine", types.SimpleNamespace(GameAction=object))
    monkeypatch.setitem(sys.modules, "game.player", types.SimpleNamespace(Player=object))
    monkeypatch.setitem(sys.modules, "tiles.tile", types.SimpleNamespace(Tile=object))

    spec = importlib.util.spec_from_file_location(
        "neural_player_under_test", "src/ai/neural_player.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.NeuralPlayer


def _player_without_init(monkeypatch):
    neural_cls = _load_neural_player_module(monkeypatch)
    return neural_cls.__new__(neural_cls)


def test_kan_kwargs_prefer_explicit_kan_lists(monkeypatch):
    player = _player_without_init(monkeypatch)

    hand = {
        "upgrade_kan_tiles": ["7sou"],
        "closed_kan_tiles": ["3man"],
        "concealed_tiles": ["7sou", "7sou", "7sou", "7sou"],
    }
    assert player._get_call_kwargs("kan", hand) == {"tile": "7sou"}

    hand2 = {
        "upgrade_kan_tiles": [],
        "closed_kan_tiles": ["3man"],
        "concealed_tiles": ["3man", "3man", "3man", "3man"],
    }
    assert player._get_random_action_kwargs("kan", hand2) == {"tile": "3man"}


def test_kan_kwargs_fallback_from_concealed_tiles_and_none_case(monkeypatch):
    player = _player_without_init(monkeypatch)

    fallback_hand = {"concealed_tiles": ["2pin", "2pin", "2pin", "2pin"]}
    assert player._get_kan_tile(fallback_hand) == "2pin"

    no_kan_hand = {"concealed_tiles": ["2pin", "2pin", "2pin"]}
    assert player._get_kan_tile(no_kan_hand) is None


def test_chii_sequence_picker_and_parser(monkeypatch):
    player = _player_without_init(monkeypatch)

    hand = {
        "last_discard": "5sou",
        "concealed_tiles": ["4sou", "6sou", "1man"],
    }
    assert player._pick_chii_sequence(hand) == ["4sou", "6sou"]
    assert player._get_call_kwargs("chii", hand) == {"sequence": ["4sou", "6sou"]}

    red_hand = {
        "last_discard": "5rsou",
        "concealed_tiles": ["3sou", "4sou", "8pin"],
    }
    assert player._pick_chii_sequence(red_hand) == ["3sou", "4sou"]

    assert player._pick_chii_sequence({"last_discard": "east", "concealed_tiles": ["1sou", "2sou"]}) == []
    assert player._parse_number_tile("5rpin") == (5, "pin")
    assert player._parse_number_tile("north") is None
