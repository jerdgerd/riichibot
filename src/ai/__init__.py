# src/ai/__init__.py
"""
AI module for neural network players
"""

from .neural_player import NeuralPlayer, MahjongNet
from .training_manager import TrainingManager
from .ai_game import AIGameManager, HumanPlayer

__all__ = ['NeuralPlayer', 'MahjongNet', 'TrainingManager', 'AIGameManager', 'HumanPlayer']
