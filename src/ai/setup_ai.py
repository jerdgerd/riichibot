#!/usr/bin/env python3
"""
Setup script for AI training environment
"""

import os
import platform
import subprocess
import sys


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True


def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")

    try:
        # Install basic requirements
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )

        # Install AI requirements
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements-ai.txt"]
        )

        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def check_gpu_support():
    """Check for GPU support"""
    try:
        import torch

        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU support available: {gpu_count}x {gpu_name}")
            return True
        else:
            print("⚠️  No GPU detected, will use CPU (slower training)")
            return False
    except ImportError:
        print("⚠️  PyTorch not installed, cannot check GPU support")
        return False


def create_directories():
    """Create necessary directories"""
    dirs = ["models", "logs", "analysis_output", "tournament_results"]

    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print(f"📁 Created directory: {dir_name}")


def run_quick_test():
    """Run a quick test to verify everything works"""
    print("🧪 Running quick test...")

    try:
        # Test imports
        sys.path.append("src")
        from ai.config import DEFAULT_CONFIG
        from ai.neural_player import NeuralPlayer
        from ai.training_manager import TrainingManager
        from tiles.tile import Wind

        print("✅ Core imports successful")

        # Test neural network creation
        player = NeuralPlayer("Test_Player", Wind.EAST)
        print("✅ Neural network creation successful")

        # Test configuration
        config = DEFAULT_CONFIG
        print(f"✅ Configuration loaded: {config.num_games} games")

        # Test game engine import
        from game.engine import MahjongEngine

        print("✅ Game engine import successful")

        print("✅ All tests passed!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def display_system_info():
    """Display system information"""
    print("💻 System Information:")
    print(f"  OS: {platform.system()} {platform.release()}")
    print(f"  Architecture: {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Platform: {platform.platform()}")


def print_next_steps():
    """Print next steps for the user"""
    print("\n🎯 Setup Complete! Next Steps:")
    print("=" * 50)
    print("1. Quick Demo (5-10 minutes):")
    print("   python src/ai/quick_start.py --mode demo")
    print()
    print("2. Standard Training (1-2 hours):")
    print("   python src/ai/quick_start.py --mode standard")
    print()
    print("3. Play Against AI:")
    print("   python src/ai/ai_game.py --model-dir models")
    print()
    print("4. Analyze Results:")
    print("   python src/ai/analyze_models.py --model-dir models --all")
    print()
    print("5. Run Tournament:")
    print("   python src/ai/tournament.py models")
    print()
    print("📚 Documentation: src/ai/README.md")
    print("🐛 Issues: Check logs/ directory for debugging")


def main():
    """Main setup function"""
    print("🤖 Riichi Mahjong AI Setup")
    print("=" * 40)

    # Check system requirements
    display_system_info()
    print()

    if not check_python_version():
        sys.exit(1)

    # Create directories
    create_directories()
    print()

    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)
    print()

    # Check GPU support
    has_gpu = check_gpu_support()
    print()

    # Run tests
    if not run_quick_test():
        print("❌ Setup failed during testing")
        sys.exit(1)
    print()

    # Success message
    print("🎉 Setup completed successfully!")

    if has_gpu:
        print("🚀 GPU acceleration available - training will be fast!")
    else:
        print("🐌 Using CPU - training will be slower but still works")

    print_next_steps()


if __name__ == "__main__":
    main()
