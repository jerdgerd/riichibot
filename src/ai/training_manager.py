import json
import os
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np

from ai.neural_player import NeuralPlayer
from game.engine import MahjongEngine
from tiles.tile import Wind


class TrainingManager:
    """Manages the training process for neural network players"""

    def __init__(self, save_dir: str = "models"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        # Training statistics
        self.training_stats = {
            "games_played": 0,
            "win_rates": [],
            "avg_scores": [],
            "training_losses": [],
        }

    def create_neural_players(self, learning_rate: float = 0.001) -> List[NeuralPlayer]:
        """Create four neural network players"""
        winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
        players = []

        for i in range(4):
            player = NeuralPlayer(f"AI_Player_{i+1}", winds[i], learning_rate)
            players.append(player)

        return players

    def train_players(
        self,
        num_games: int = 1000,
        save_interval: int = 100,
        learning_rate: float = 0.001,
    ):
        """Train neural network players through self-play"""
        print(f"Starting training for {num_games} games...")

        # Create players
        neural_players = self.create_neural_players(learning_rate=learning_rate)

        # Load existing models if available
        for i, player in enumerate(neural_players):
            model_path = os.path.join(self.save_dir, f"player_{i+1}_model.pth")
            if os.path.exists(model_path):
                player.load_model(model_path)
                print(f"Loaded existing model for {player.name}")

        game_results = []

        for game_num in range(num_games):
            print(f"\nGame {game_num + 1}/{num_games}")

            # Create game with neural players
            player_names = [p.name for p in neural_players]
            game = MahjongEngine(player_names)

            # Replace default players with neural players
            game.players = neural_players

            # Play the game
            result = self.play_training_game(game, neural_players)
            game_results.append(result)

            # Update statistics
            self.update_training_stats(neural_players, result)

            # Save models periodically
            if (game_num + 1) % save_interval == 0:
                self.save_all_models(neural_players)
                self.save_training_stats()
                self.plot_training_progress()
                print(f"Saved models and stats at game {game_num + 1}")

        # Final save
        self.save_all_models(neural_players)
        self.save_training_stats()
        self.plot_training_progress()

        print("\nTraining completed!")
        self.print_final_stats(neural_players)

    def play_training_game(
        self, game: MahjongEngine, players: List[NeuralPlayer]
    ) -> Dict[str, Any]:
        """Play a single training game"""
        max_turns = 200  # Prevent infinite games
        turn_count = 0
        result: Dict[str, Any] = {"winner": -1}

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

            # Give immediate reward based on action result
            if result["success"]:
                reward = self.calculate_action_reward(action, result, player_hand)
                current_player.give_reward(reward)
            else:
                current_player.give_reward(-1.0)  # Penalty for invalid actions

            # Check if game ended
            if result.get("game_ended", False):
                winner_idx = result.get("winner")
                final_scores = [p.score for p in game.players]

                # Give final rewards
                for i, player in enumerate(players):
                    won = i == winner_idx
                    player.update_game_result(won, final_scores[i])

                break

            # Advance turn if no calls were made
            if game.last_discard is None:
                game.advance_turn()

            turn_count += 1

        # Handle draw case
        if turn_count >= max_turns:
            final_scores = [p.score for p in game.players]
            for i, player in enumerate(players):
                player.update_game_result(False, final_scores[i])

        return {
            "winner": result.get("winner", -1),
            "final_scores": [p.score for p in game.players],
            "turns": turn_count,
            "game_ended_normally": turn_count < max_turns,
        }

    def calculate_action_reward(
        self, action: str, result: Dict[str, Any], player_hand: Dict[str, Any]
    ) -> float:
        """Calculate reward for a specific action"""
        base_reward = 0.1  # Small positive reward for valid actions

        if action == "tsumo" or action == "ron":
            return 20.0  # Large reward for winning
        elif action == "riichi":
            return 2.0  # Good reward for riichi
        elif action == "discard":
            # Small reward for maintaining tenpai
            if player_hand.get("is_tenpai", False):
                return 0.5
            return base_reward
        elif action in ["chii", "pon", "kan"]:
            return 1.0  # Moderate reward for calls

        return base_reward

    def update_training_stats(
        self, players: List[NeuralPlayer], result: Dict[str, Any]
    ):
        """Update training statistics"""
        self.training_stats["games_played"] += 1

        # Calculate win rates
        win_rates = []
        avg_losses = []
        avg_scores = []

        for player in players:
            stats = player.get_stats()
            win_rates.append(stats["win_rate"])
            avg_losses.append(stats["avg_recent_loss"])
            avg_scores.append(player.score)

        self.training_stats["win_rates"].append(win_rates)
        self.training_stats["training_losses"].append(avg_losses)
        self.training_stats["avg_scores"].append(avg_scores)

    def save_all_models(self, players: List[NeuralPlayer]):
        """Save all player models"""
        for i, player in enumerate(players):
            model_path = os.path.join(self.save_dir, f"player_{i+1}_model.pth")
            player.save_model(model_path)

    def save_training_stats(self):
        """Save training statistics to JSON"""
        stats_path = os.path.join(self.save_dir, "training_stats.json")
        with open(stats_path, "w") as f:
            json.dump(self.training_stats, f, indent=2)

    def plot_training_progress(self):
        """Plot training progress graphs"""
        if len(self.training_stats["win_rates"]) < 10:
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        # Win rates over time
        win_rates = np.array(self.training_stats["win_rates"])
        games = range(len(win_rates))

        for i in range(4):
            ax1.plot(games, win_rates[:, i], label=f"Player {i+1}")
        ax1.set_title("Win Rates Over Time")
        ax1.set_xlabel("Games")
        ax1.set_ylabel("Win Rate")
        ax1.legend()
        ax1.grid(True)

        # Average scores over time
        avg_scores = np.array(self.training_stats["avg_scores"])
        for i in range(4):
            ax2.plot(games, avg_scores[:, i], label=f"Player {i+1}")
        ax2.set_title("Average Scores Over Time")
        ax2.set_xlabel("Games")
        ax2.set_ylabel("Score")
        ax2.legend()
        ax2.grid(True)

        # Training losses
        losses = np.array(self.training_stats["training_losses"])
        for i in range(4):
            ax3.plot(games, losses[:, i], label=f"Player {i+1}")
        ax3.set_title("Training Losses Over Time")
        ax3.set_xlabel("Games")
        ax3.set_ylabel("Loss")
        ax3.legend()
        ax3.grid(True)

        # Win rate distribution (recent 100 games)
        recent_wins = win_rates[-100:] if len(win_rates) >= 100 else win_rates
        ax4.boxplot(
            [recent_wins[:, i] for i in range(4)],
            labels=[f"Player {i+1}" for i in range(4)],
        )
        ax4.set_title("Recent Win Rate Distribution")
        ax4.set_ylabel("Win Rate")
        ax4.grid(True)

        plt.tight_layout()
        plt.savefig(os.path.join(self.save_dir, "training_progress.png"))
        plt.close()

    def print_final_stats(self, players: List[NeuralPlayer]):
        """Print final training statistics"""
        print("\n" + "=" * 50)
        print("FINAL TRAINING STATISTICS")
        print("=" * 50)

        for i, player in enumerate(players):
            stats = player.get_stats()
            print(f"\n{player.name}:")
            print(f"  Total Games: {stats['total_games']}")
            print(f"  Wins: {stats['wins']}")
            print(f"  Win Rate: {stats['win_rate']:.3f}")
            print(f"  Final Epsilon: {stats['epsilon']:.3f}")
            print(f"  Memory Size: {stats['memory_size']}")
            print(f"  Training Steps: {stats['training_steps']}")
            print(f"  Recent Avg Loss: {stats['avg_recent_loss']:.4f}")

    def evaluate_players(self, num_eval_games: int = 100) -> Dict[str, Any]:
        """Evaluate trained players with epsilon=0 (no exploration)"""
        print(f"\nEvaluating players over {num_eval_games} games...")

        # Create players for evaluation
        neural_players = self.create_neural_players()

        # Load trained models
        for i, player in enumerate(neural_players):
            model_path = os.path.join(self.save_dir, f"player_{i+1}_model.pth")
            if os.path.exists(model_path):
                player.load_model(model_path)
                player.epsilon = 0.0  # No exploration during evaluation

        eval_results = []

        for game_num in range(num_eval_games):
            if (game_num + 1) % 10 == 0:
                print(f"Evaluation game {game_num + 1}/{num_eval_games}")

            # Create game
            player_names = [p.name for p in neural_players]
            game = MahjongEngine(player_names)
            game.players = neural_players

            # Play game
            result = self.play_training_game(game, neural_players)
            eval_results.append(result)

        # Calculate evaluation statistics
        eval_stats = self.calculate_eval_stats(eval_results, neural_players)

        print("\nEVALUATION RESULTS:")
        print("=" * 30)
        for i, player in enumerate(neural_players):
            print(f"{player.name}: {eval_stats['win_rates'][i]:.3f} win rate")

        return eval_stats

    def calculate_eval_stats(
        self, results: List[Dict[str, Any]], players: List[NeuralPlayer]
    ) -> Dict[str, Any]:
        """Calculate evaluation statistics"""
        if not results:
            return {
                "win_rates": [0.0] * 4,
                "avg_scores": [0.0] * 4,
                "total_games": 0,
                "wins": [0] * 4,
            }

        wins = [0] * 4
        total_scores = [0] * 4

        for result in results:
            winner = result["winner"]
            if winner >= 0:
                wins[winner] += 1

            for i, score in enumerate(result["final_scores"]):
                total_scores[i] += score

        num_games = len(results)
        win_rates = [w / num_games for w in wins]
        avg_scores = [s / num_games for s in total_scores]

        return {
            "win_rates": win_rates,
            "avg_scores": avg_scores,
            "total_games": num_games,
            "wins": wins,
        }
