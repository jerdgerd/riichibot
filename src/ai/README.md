# Riichi Mahjong AI Training System

This module provides a complete neural network-based AI training system for Riichi Mahjong players.

## Quick Start

```bash
# Install AI dependencies
pip install -r requirements-ai.txt

# Quick demo (100 games)
python src/ai/quick_start.py --mode demo

# Play against trained AI
python src/ai/ai_game.py --model-dir models

# Analyze training results
python src/ai/analyze_models.py --model-dir models --all
```

## Training Modes
# Demo Mode
Games: 100
Purpose: Quick testing and validation
Time: ~10-15 minutes
```bash
python src/ai/quick_start.py --mode demo
```

# Fast Mode
Games: 500
Purpose: Rapid prototyping
Time: ~30-45 minutes
```bash
python src/ai/quick_start.py --mode fast
```

# Standard Mode
Games: 1000
Purpose: Balanced training
Time: ~1-2 hours
```bash
python src/ai/quick_start.py --mode standard
```

# Deep Mode
Games: 5000
Purpose: High-quality models
Time: ~4-6 hours
```bash
python src/ai/quick_start.py --mode deep
```

## Advanced Training
# Custom Configuration
```bash
# Create custom config
python -c "
from ai.config import TrainingConfig
config = TrainingConfig(num_games=2000, learning_rate=0.0005)
config.save('my_config.json')
"
# Train with custom config
python src/ai/enhanced_train_ai.py --config-file my_config.json
```

# Resume Training
```bash
python src/ai/enhanced_train_ai.py --resume --save-dir models
```

## Model Analysis
# Performance Analysis
```bash
python src/ai/analyze_models.py --model-dir models --all
```

# Speed Benchmarks
```bash
python src/ai/analyze_models.py --model-dir models --benchmark
```

# Model Comparison
```bash
python src/ai/utils.py compare_models models_v1 models_v2
```

## Tournament System
# Single Elimination
```bash
python src/ai/tournament.py models_v1 models_v2 models_v3 --type elimination
```
# Round Robin
```bash
python src/ai/tournament.py models_v1 models_v2 models_v3      --type round-robin
```

## File Structure
```bash
src/ai/
├── __init__.py              # Module initialization
├── neural_player.py         # Neural network player implementation
├── training_manager.py      # Basic training manager
├── enhanced_training_manager.py  # Advanced training with metrics
├── config.py               # Training configurations
├── logger.py               # Training logging
├── metrics.py              # Performance analysis
├── utils.py                # Utility functions
├── ai_game.py              # Human vs AI gameplay
├── train_ai.py             # Basic training script
├── enhanced_train_ai.py    # Advanced training script
├── quick_start.py          # Quick start script
├── analyze_models.py       # Model analysis script
├── tournament.py           # Tournament system
└── README.md              # This file
```

## Neural Network Architecture
The AI uses a multi-head neural network:

Input: 400 features (hand state, game context, opponent info)
Hidden Layers: 512 → 512 → 256 neurons
Output Heads:
Discard: 34 tile types
Calls: chii, pon, kan, pass
Riichi: yes/no
Win: ron/tsumo/no

# Training Process
Self-Play: 4 AI players play against each other
Experience Replay: Store and replay game experiences
Q-Learning: Update neural networks based on rewards
Exploration: Epsilon-greedy action selection
Evaluation: Periodic testing with no exploration

# Reward System
Win: +20 points
Riichi: +2 points
Tenpai: +0.5 points
Valid Action: +0.1 points
Invalid Action: -1 point
Final Score Bonus: Based on game score

# Configuration Options
Key parameters you can adjust:

num_games: Number of training games
learning_rate: Neural network learning rate
epsilon_decay: Exploration decay rate
batch_size: Training batch size
memory_size: Experience replay buffer size
hidden_size: Neural network size

## Troubleshooting
# Common Issues
CUDA Out of Memory

Reduce batch_size in config
Use CPU: set CUDA_VISIBLE_DEVICES=""
Training Too Slow

Use --mode fast for quick testing
Reduce num_games in config
Models Not Learning

Increase learning_rate
Check reward system
Verify game logic

# Performance Tips
GPU Training: Ensure PyTorch CUDA is installed
Parallel Training: Use multiple processes for evaluation
Memory Management: Monitor RAM usage during training
Checkpointing: Save models frequently to prevent loss

## Advanced Features
# Custom Reward Functions
Modify calculate_enhanced_reward() in enhanced_training_manager.py

# Network Architecture Changes
Modify MahjongNet class in neural_player.py

# Custom Metrics
Add new metrics to PerformanceAnalyzer in metrics.py

# Integration with Web Interface
The trained models can be loaded into the web server for online play. `

