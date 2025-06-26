# src/ai/config.py
"""
Configuration settings for AI training
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class TrainingConfig:
    """Configuration for neural network training"""

    # Network architecture
    input_size: int = 400
    hidden_size: int = 512
    learning_rate: float = 0.001

    # Training parameters
    batch_size: int = 32
    memory_size: int = 10000
    target_update_freq: int = 100

    # Exploration parameters
    epsilon_start: float = 1.0
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995

    # Reward parameters
    win_reward: float = 20.0
    riichi_reward: float = 2.0
    tenpai_reward: float = 0.5
    base_reward: float = 0.1
    invalid_action_penalty: float = -1.0

    # Training schedule
    num_games: int = 1000
    save_interval: int = 100
    eval_interval: int = 200
    eval_games: int = 50

    # Discount factor for Q-learning
    gamma: float = 0.99

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "input_size": self.input_size,
            "hidden_size": self.hidden_size,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "memory_size": self.memory_size,
            "target_update_freq": self.target_update_freq,
            "epsilon_start": self.epsilon_start,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "win_reward": self.win_reward,
            "riichi_reward": self.riichi_reward,
            "tenpai_reward": self.tenpai_reward,
            "base_reward": self.base_reward,
            "invalid_action_penalty": self.invalid_action_penalty,
            "num_games": self.num_games,
            "save_interval": self.save_interval,
            "eval_interval": self.eval_interval,
            "eval_games": self.eval_games,
            "gamma": self.gamma,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TrainingConfig":
        """Create config from dictionary"""
        return cls(**config_dict)

    def save(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "TrainingConfig":
        """Load configuration from JSON file"""
        with open(filepath, "r") as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)


# Default configurations for different training scenarios
DEFAULT_CONFIG = TrainingConfig()

FAST_TRAINING_CONFIG = TrainingConfig(
    num_games=500,
    save_interval=50,
    eval_interval=100,
    learning_rate=0.01,
    epsilon_start=1.0,  # full exploration at start
    epsilon_min=0.05,  # don't drop to near-zero too soon
    epsilon_decay=0.997,  # slower decay → longer exploration
    memory_size=15000,  # allow more varied experience
    batch_size=64,  # slightly bigger batches for stability
)

DEEP_TRAINING_CONFIG = TrainingConfig(
    num_games=5000,
    save_interval=200,
    eval_interval=500,
    hidden_size=1024,
    learning_rate=0.0005,
    epsilon_decay=0.999,
)
