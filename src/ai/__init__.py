"""AI module package exports (lazy-loaded)."""

__all__ = [
    "NeuralPlayer",
    "MahjongNet",
    "TrainingManager",
    "AIGameManager",
    "HumanPlayer",
]


def __getattr__(name):
    if name in {"NeuralPlayer", "MahjongNet"}:
        from .neural_player import MahjongNet, NeuralPlayer

        return {"NeuralPlayer": NeuralPlayer, "MahjongNet": MahjongNet}[name]
    if name == "TrainingManager":
        from .training_manager import TrainingManager

        return TrainingManager
    if name in {"AIGameManager", "HumanPlayer"}:
        from .ai_game import AIGameManager, HumanPlayer

        return {"AIGameManager": AIGameManager, "HumanPlayer": HumanPlayer}[name]
    raise AttributeError(name)
