# src/ai/train_ai.py
#!/usr/bin/env python3
"""
Training script for neural network Mahjong players
"""

import argparse
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from ai.training_manager import TrainingManager


def main():
    parser = argparse.ArgumentParser(description="Train neural network Mahjong players")
    parser.add_argument(
        "--games",
        type=int,
        default=1000,
        help="Number of training games (default: 1000)",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=100,
        help="Save models every N games (default: 100)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.001,
        help="Learning rate for neural networks (default: 0.001)",
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        default="models",
        help="Directory to save models (default: models)",
    )
    parser.add_argument(
        "--eval-games",
        type=int,
        default=100,
        help="Number of evaluation games (default: 100)",
    )
    parser.add_argument(
        "--eval-only", action="store_true", help="Only run evaluation, skip training"
    )

    args = parser.parse_args()

    # Create training manager
    trainer = TrainingManager(save_dir=args.save_dir)

    if args.eval_only:
        # Run evaluation only
        trainer.evaluate_players(args.eval_games)
    else:
        # Run training
        trainer.train_players(num_games=args.games, save_interval=args.save_interval)

        # Run evaluation after training
        trainer.evaluate_players(args.eval_games)


if __name__ == "__main__":
    main()
