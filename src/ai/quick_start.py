# src/ai/quick_start.py
#!/usr/bin/env python3
"""
Quick start script for AI training
"""

import argparse
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ai.config import FAST_TRAINING_CONFIG, DEFAULT_CONFIG, DEEP_TRAINING_CONFIG
from ai.enhanced_training_manager import EnhancedTrainingManager

def main():
    parser = argparse.ArgumentParser(description='Quick start AI training')
    parser.add_argument('--mode', choices=['demo', 'fast', 'standard', 'deep'], 
                       default='demo', help='Training mode')
    parser.add_argument('--save-dir', type=str, default='models',
                       help='Directory to save models')
    
    args = parser.parse_args()
    
    print("🤖 Riichi Mahjong AI Quick Start")
    print("=" * 40)
    
    if args.mode == 'demo':
        print("🚀 Demo Mode: 100 games for quick testing")
        config = FAST_TRAINING_CONFIG
        config.num_games = 100
        config.save_interval = 25
        config.eval_interval = 50
    elif args.mode == 'fast':
        print("⚡ Fast Mode: 500 games with aggressive learning")
        config = FAST_TRAINING_CONFIG
    elif args.mode == 'standard':
        print("📚 Standard Mode: 1000 games with balanced learning")
        config = DEFAULT_CONFIG
    elif args.mode == 'deep':
        print("🧠 Deep Mode: 5000 games with large network")
        config = DEEP_TRAINING_CONFIG
    
    print(f"Configuration:")
    print(f"  Games: {config.num_games}")
    print(f"  Learning Rate: {config.learning_rate}")
    print(f"  Network Size: {config.hidden_size}")
    print(f"  Save Directory: {args.save_dir}")
    
    # Create experiment name
    from datetime import datetime
    experiment_name = f"quickstart_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create trainer
    trainer = EnhancedTrainingManager(
        config=config,
        save_dir=args.save_dir,
        experiment_name=experiment_name
    )
    
    print(f"\n🎯 Starting training...")
    print(f"Experiment: {experiment_name}")
    
    try:
        # Start training
        trainer.train_players()
        
        print("\n✅ Training completed successfully!")
        print(f"Models saved in: {args.save_dir}")
        print(f"Logs saved in: logs/")
        
        # Quick test
        print("\n🎮 Testing trained models...")
        from ai.utils import validate_model_consistency
        validation = validate_model_consistency(args.save_dir)
        
        if validation['all_models_present'] and all(validation['models_loadable']):
            print("✅ All models working correctly!")
            print("\nNext steps:")
            print(f"  1. Play against AI: python src/ai/ai_game.py --model-dir {args.save_dir}")
            print(f"  2. Analyze models: python src/ai/analyze_models.py --model-dir {args.save_dir} --all")
            print(f"  3. Run tournament: python src/ai/tournament.py {args.save_dir}")
        else:
            print("⚠️  Some models may have issues. Check the validation results.")
            
    except KeyboardInterrupt:
        print("\n⏹️  Training interrupted by user")
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        print("Check the logs for more details.")

if __name__ == "__main__":
    main()
