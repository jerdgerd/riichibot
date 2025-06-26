# src/ai/logger.py
"""
Logging and monitoring utilities for AI training
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List


class TrainingLogger:
    """Logger for training progress and statistics"""

    def __init__(self, log_dir: str = "logs", experiment_name: str = None):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        if experiment_name is None:
            experiment_name = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.experiment_name = experiment_name
        self.log_file = os.path.join(log_dir, f"{experiment_name}.log")
        self.stats_file = os.path.join(log_dir, f"{experiment_name}_stats.json")

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.log_file), logging.StreamHandler()],
        )

        self.logger = logging.getLogger(experiment_name)
        self.training_stats = []
        self.start_time = time.time()

    def log_game_result(
        self, game_num: int, result: Dict[str, Any], player_stats: List[Dict[str, Any]]
    ):
        """Log results from a single game"""
        self.logger.info(
            f"Game {game_num}: Winner={result.get('winner', -1)}, "
            f"Turns={result.get('turns', 0)}"
        )

        # Store detailed stats
        game_stats = {
            "game_number": game_num,
            "timestamp": time.time(),
            "result": result,
            "player_stats": player_stats,
        }

        self.training_stats.append(game_stats)

    def log_training_milestone(self, milestone: str, stats: Dict[str, Any]):
        """Log training milestones"""
        self.logger.info(f"MILESTONE - {milestone}: {stats}")

    def log_evaluation_results(self, eval_stats: Dict[str, Any]):
        """Log evaluation results"""
        self.logger.info("EVALUATION RESULTS:")
        for i, win_rate in enumerate(eval_stats["win_rates"]):
            self.logger.info(f"  Player {i+1}: {win_rate:.3f} win rate")

    def save_stats(self):
        """Save training statistics to file"""
        with open(self.stats_file, "w") as f:
            json.dump(
                {
                    "experiment_name": self.experiment_name,
                    "start_time": self.start_time,
                    "training_stats": self.training_stats,
                },
                f,
                indent=2,
            )

    def get_training_duration(self) -> float:
        """Get training duration in seconds"""
        return time.time() - self.start_time
