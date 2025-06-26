# src/ai/__init__.py
"""
AI module for neural network players
"""

from .ai_game import AIGameManager, HumanPlayer
from .neural_player import MahjongNet, NeuralPlayer
from .training_manager import TrainingManager

__all__ = [
    "NeuralPlayer",
    "MahjongNet",
    "TrainingManager",
    "AIGameManager",
    "HumanPlayer",
]
