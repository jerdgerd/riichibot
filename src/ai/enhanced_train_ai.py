#!/usr/bin/env python3
"""
Enhanced training script for neural network Mahjong players
"""

import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ai.enhanced_training_manager import EnhancedTrainingManager
from ai.config import TrainingConfig, DEFAULT_CONFIG, FAST_TRAINING_CONFIG, DEEP_TRAINING_CONFIG

def main():
    parser = argparse.ArgumentParser(description='Enhanced training for neural network Mahjong players')
    parser.add_argument('--config', type=str, choices=['default', 'fast', 'deep'], 
                       default='default', help='Training configuration preset')
    parser.add_argument('--config-file', type=str, 
                       help='Path to custom configuration JSON file')
    parser.add_argument('--save-dir', type=str, default='models',
                       help='Directory to save models (default: models)')
    parser.add_argument('--experiment-name', type=str,
                       help='Name for this training experiment')
    parser.add_argument('--resume', action='store_true',
                       help='Resume training from existing models')
    
    # Override specific config parameters
    parser.add_argument('--games', type=int, help='Number of training games')
    parser.add_argument('--learning-rate', type=float, help='Learning rate')
    parser.add_argument('--batch-size', type=int, help='Batch size')
    parser.add_argument('--epsilon-decay', type=float, help='Epsilon decay rate')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config_file:
        config = TrainingConfig.load(args.config_file)
    else:
        config_map = {
            'default': DEFAULT_CONFIG,
            'fast': FAST_TRAINING_CONFIG,
            'deep': DEEP_TRAINING_CONFIG
        }
        config = config_map[args.config]
    
    # Override config with command line arguments
    if args.games:
        config.num_games = args.games
    if args.learning_rate:
        config.learning_rate = args.learning_rate
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.epsilon_decay:
        config.epsilon_decay = args.epsilon_decay
    
    print(f"Training Configuration:")
    print(f"  Games: {config.num_games}")
    print(f"  Learning Rate: {config.learning_rate}")
    print(f"  Batch Size: {config.batch_size}")
    print(f"  Epsilon Decay: {config.epsilon_decay}")
    print(f"  Save Directory: {args.save_dir}")
    
    # Create enhanced training manager
    trainer = EnhancedTrainingManager(
        config=config,
        save_dir=args.save_dir,
        experiment_name=args.experiment_name
    )
    
    # Start training
    trainer.train_players()

if __name__ == "__main__":
    main()
