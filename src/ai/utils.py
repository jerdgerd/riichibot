import json
import os
from typing import Any, Dict, List

import torch

from ai.config import TrainingConfig
from ai.neural_player import NeuralPlayer
from tiles.tile import Wind


def load_trained_models(model_dir: str) -> List[NeuralPlayer]:
    """Load all trained models from directory"""
    winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
    players = []
    for i in range(4):
        player = NeuralPlayer(f"AI_Player_{i+1}", winds[i])
        model_path = os.path.join(model_dir, f"player_{i+1}_model.pth")

        if os.path.exists(model_path):
            player.load_model(model_path)
            player.epsilon = 0.0  # No exploration for loaded models
            print(f"Loaded model for {player.name}")
        else:
            print(f"No model found for {player.name}, using random play")

        players.append(player)

    return players


def compare_models(
    model_dir1: str, model_dir2: str, num_games: int = 100
) -> Dict[str, Any]:
    """Compare two sets of trained models"""
    from game.engine import MahjongEngine

    print(f"Comparing models: {model_dir1} vs {model_dir2}")

    # Load both sets of models
    players1 = load_trained_models(model_dir1)
    players2 = load_trained_models(model_dir2)

    # Create mixed games (2 players from each model)
    results = []

    for game_num in range(num_games):
        # Alternate which models go first
        if game_num % 2 == 0:
            mixed_players = [players1[0], players1[1], players2[0], players2[1]]
            team1_indices = [0, 1]
            team2_indices = [2, 3]
        else:
            mixed_players = [players2[0], players2[1], players1[0], players1[1]]
            team1_indices = [2, 3]
            team2_indices = [0, 1]

        # Play game
        player_names = [p.name for p in mixed_players]
        game = MahjongEngine(player_names)
        game.players = mixed_players

        result = play_single_game(game, mixed_players)

        # Determine which team won
        winner = result.get("winner", -1)
        if winner in team1_indices:
            team_winner = 1 if game_num % 2 == 0 else 2
        elif winner in team2_indices:
            team_winner = 2 if game_num % 2 == 0 else 1
        else:
            team_winner = 0  # Draw

        results.append(
            {
                "winner": winner,
                "team_winner": team_winner,
                "scores": result["final_scores"],
            }
        )

    # Calculate statistics
    team1_wins = sum(1 for r in results if r["team_winner"] == 1)
    team2_wins = sum(1 for r in results if r["team_winner"] == 2)
    draws = sum(1 for r in results if r["team_winner"] == 0)

    return {
        "model1_wins": team1_wins,
        "model2_wins": team2_wins,
        "draws": draws,
        "model1_win_rate": team1_wins / num_games,
        "model2_win_rate": team2_wins / num_games,
        "total_games": num_games,
    }


def play_single_game(game, players) -> Dict[str, Any]:
    """Play a single game and return results"""
    max_turns = 200
    turn_count = 0

    while game.phase.value != "ended" and turn_count < max_turns:
        current_player_idx = game.current_player
        current_player = players[current_player_idx]

        # Get game state and player hand
        game_state = game.get_game_state()
        player_hand = game.get_player_hand(current_player_idx)
        valid_actions = game.get_valid_actions(current_player_idx)

        # Player chooses action
        action, kwargs = current_player.choose_action(
            game_state, player_hand, valid_actions
        )

        # Execute action
        result = game.execute_action(current_player_idx, action, **kwargs)

        # Check if game ended
        if result.get("game_ended", False):
            break

        # Advance turn if no calls were made
        if game.last_discard is None:
            game.advance_turn()

        turn_count += 1

    return {
        "winner": result.get("winner", -1),
        "final_scores": [p.score for p in game.players],
        "turns": turn_count,
        "game_ended_normally": turn_count < max_turns,
    }


def analyze_model_performance(model_dir: str) -> Dict[str, Any]:
    """Analyze performance of trained models"""
    stats_file = os.path.join(model_dir, "training_stats.json")
    if not os.path.exists(stats_file):
        return {"error": "No training stats found"}

    with open(stats_file, "r") as f:
        stats = json.load(f)

    # Load models to get current statistics
    players = load_trained_models(model_dir)

    analysis = {
        "total_training_games": stats.get("games_played", 0),
        "final_win_rates": [],
        "final_epsilons": [],
        "model_sizes": [],
    }

    for i, player in enumerate(players):
        player_stats = player.get_stats()
        analysis["final_win_rates"].append(player_stats["win_rate"])
        analysis["final_epsilons"].append(player_stats["epsilon"])

        # Get model size
        model_path = os.path.join(model_dir, f"player_{i+1}_model.pth")
        if os.path.exists(model_path):
            model_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
            analysis["model_sizes"].append(model_size)
        else:
            analysis["model_sizes"].append(0)

    return analysis


def export_model_for_deployment(model_dir: str, output_dir: str):
    """Export models in a format suitable for deployment"""
    os.makedirs(output_dir, exist_ok=True)
    # Load configuration
    config_path = os.path.join(model_dir, "training_config.json")
    if os.path.exists(config_path):
        config = TrainingConfig.load(config_path)
    else:
        config = TrainingConfig()

    # Export each model
    for i in range(4):
        model_path = os.path.join(model_dir, f"player_{i+1}_model.pth")
        if os.path.exists(model_path):
            # Load model
            checkpoint = torch.load(model_path, map_location="cpu")

            # Create deployment package
            deployment_package = {
                "model_state_dict": checkpoint["model_state_dict"],
                "config": config.to_dict(),
                "training_stats": {
                    "total_games": checkpoint.get("total_games", 0),
                    "wins": checkpoint.get("wins", 0),
                    "training_steps": checkpoint.get("training_steps", 0),
                },
            }

            # Save deployment package
            output_path = os.path.join(output_dir, f"ai_player_{i+1}_deployment.pth")
            torch.save(deployment_package, output_path)
            print(f"Exported {output_path}")


def create_tournament_bracket(
    model_dirs: List[str], num_games_per_match: int = 50
) -> Dict[str, Any]:
    """Create a tournament between different model versions"""
    from itertools import combinations

    tournament_results = {}

    # Play all combinations of model pairs
    for i, (dir1, dir2) in enumerate(combinations(model_dirs, 2)):
        match_name = f"{os.path.basename(dir1)}_vs_{os.path.basename(dir2)}"
        print(f"Playing match: {match_name}")

        result = compare_models(dir1, dir2, num_games_per_match)
        tournament_results[match_name] = result

    return tournament_results


def visualize_training_progress(model_dir: str, save_path: str = None):
    """Create comprehensive visualization of training progress"""
    stats_file = os.path.join(model_dir, "training_stats.json")
    if not os.path.exists(stats_file):
        print("No training stats found")
        return

    with open(stats_file, "r") as f:
        stats = json.load(f)

    if not stats.get("win_rates"):
        print("No win rate data found")
        return

    win_rates = np.array(stats["win_rates"])
    avg_scores = np.array(stats["avg_scores"])
    training_losses = np.array(stats["training_losses"])

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Win rates over time
    games = range(len(win_rates))
    for i in range(4):
        ax1.plot(games, win_rates[:, i], label=f"Player {i+1}", linewidth=2)
    ax1.set_title("Win Rates Over Time", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Games")
    ax1.set_ylabel("Win Rate")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 1)

    # Average scores over time
    for i in range(4):
        ax2.plot(games, avg_scores[:, i], label=f"Player {i+1}", linewidth=2)
    ax2.set_title("Average Scores Over Time", fontsize=14, fontweight="bold")
    ax2.set_xlabel("Games")
    ax2.set_ylabel("Score")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=25000, color="red", linestyle="--", alpha=0.5, label="Starting Score")

    # Training losses
    for i in range(4):
        # Smooth the loss curve
        if len(training_losses) > 10:
            smoothed_losses = np.convolve(
                training_losses[:, i], np.ones(10) / 10, mode="valid"
            )
            smooth_games = range(9, len(training_losses))
            ax3.plot(smooth_games, smoothed_losses, label=f"Player {i+1}", linewidth=2)
    ax3.set_title("Training Losses (Smoothed)", fontsize=14, fontweight="bold")
    ax3.set_xlabel("Games")
    ax3.set_ylabel("Loss")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_yscale("log")

    # Final performance comparison
    if len(win_rates) >= 100:
        recent_win_rates = win_rates[-100:].mean(axis=0)
        players = [f"Player {i+1}" for i in range(4)]
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

        bars = ax4.bar(
            players, recent_win_rates, color=colors, alpha=0.7, edgecolor="black"
        )
        ax4.set_title(
            "Final Performance (Last 100 Games)", fontsize=14, fontweight="bold"
        )
        ax4.set_ylabel("Win Rate")
        ax4.set_ylim(0, max(recent_win_rates) * 1.2)
        ax4.grid(True, alpha=0.3, axis="y")

        # Add value labels on bars
        for bar, rate in zip(bars, recent_win_rates):
            height = bar.get_height()
            ax4.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 0.01,
                f"{rate:.3f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Visualization saved to {save_path}")
    else:
        plt.show()

    plt.close()


def benchmark_model_speed(
    model_dir: str, num_decisions: int = 1000
) -> Dict[str, float]:
    """Benchmark decision-making speed of trained models"""
    import time

    from game.engine import MahjongEngine

    players = load_trained_models(model_dir)

    # Create a dummy game state for benchmarking
    player_names = [p.name for p in players]
    game = MahjongEngine(player_names)
    game.players = players

    benchmark_results = {}

    for i, player in enumerate(players):
        start_time = time.time()

        for _ in range(num_decisions):
            game_state = game.get_game_state()
            player_hand = game.get_player_hand(i)
            valid_actions = game.get_valid_actions(i)

            # Make decision (but don't execute)
            action, kwargs = player.choose_action(
                game_state, player_hand, valid_actions
            )

        end_time = time.time()
        total_time = end_time - start_time
        decisions_per_second = num_decisions / total_time

        benchmark_results[player.name] = {
            "decisions_per_second": decisions_per_second,
            "avg_decision_time_ms": (total_time / num_decisions) * 1000,
            "total_time_seconds": total_time,
        }

    return benchmark_results


def get_model_complexity(model_dir: str) -> Dict[str, Any]:
    """Analyze model complexity and parameters"""
    complexity_results = {}

    for i in range(4):
        model_path = os.path.join(model_dir, f"player_{i+1}_model.pth")
        if os.path.exists(model_path):
            # Load model to analyze
            from ai.neural_player import MahjongNet

            net = MahjongNet()
            checkpoint = torch.load(model_path, map_location="cpu")
            net.load_state_dict(checkpoint["model_state_dict"])

            # Count parameters
            total_params = sum(p.numel() for p in net.parameters())
            trainable_params = sum(
                p.numel() for p in net.parameters() if p.requires_grad
            )

            # Model size
            model_size_mb = os.path.getsize(model_path) / (1024 * 1024)

            complexity_results[f"player_{i+1}"] = {
                "total_parameters": total_params,
                "trainable_parameters": trainable_params,
                "model_size_mb": model_size_mb,
                "architecture": {
                    "input_size": 400,
                    "hidden_size": 512,
                    "output_heads": 4,
                },
            }

    return complexity_results


def validate_model_consistency(model_dir: str) -> Dict[str, Any]:
    """Validate that all models are consistent and working"""
    validation_results = {
        "all_models_present": True,
        "models_loadable": [],
        "architecture_consistent": True,
        "errors": [],
    }

    try:
        players = load_trained_models(model_dir)

        # Check if all 4 models are present
        if len(players) != 4:
            validation_results["all_models_present"] = False
            validation_results["errors"].append(
                f"Expected 4 models, found {len(players)}"
            )

        # Test each model
        for i, player in enumerate(players):
            try:
                # Test model loading
                model_path = os.path.join(model_dir, f"player_{i+1}_model.pth")
                if os.path.exists(model_path):
                    validation_results["models_loadable"].append(True)

                    # Test inference
                    dummy_state = torch.zeros(400)
                    dummy_hand = {
                        "concealed_tiles": ["1sou"],
                        "melds": [],
                        "is_tenpai": False,
                        "can_riichi": False,
                    }
                    dummy_game_state = {
                        "current_player": 0,
                        "dealer": 0,
                        "round_number": 1,
                        "wall_tiles_remaining": 70,
                        "dora_indicators": ["1pin"],
                        "players": [
                            {
                                "name": "Test",
                                "score": 25000,
                                "hand_size": 13,
                                "melds": 0,
                                "discards": [],
                                "is_riichi": False,
                                "is_tenpai": False,
                                "is_dealer": True,
                            }
                        ]
                        * 4,
                    }

                    # Test action selection
                    action, kwargs = player.choose_action(
                        dummy_game_state, dummy_hand, ["discard", "pass"]
                    )

                else:
                    validation_results["models_loadable"].append(False)
                    validation_results["errors"].append(
                        f"Model file missing: player_{i+1}_model.pth"
                    )

            except Exception as e:
                validation_results["models_loadable"].append(False)
                validation_results["errors"].append(
                    f"Error testing player {i+1}: {str(e)}"
                )

    except Exception as e:
        validation_results["errors"].append(f"General validation error: {str(e)}")

    return validation_results
