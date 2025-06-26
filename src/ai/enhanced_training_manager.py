import json
import os
import time
from typing import Any, Dict, List

from ai.config import TrainingConfig
from ai.logger import TrainingLogger
from ai.metrics import PerformanceAnalyzer
from ai.neural_player import NeuralPlayer
from game.engine import MahjongEngine
from tiles.tile import Wind


class EnhancedTrainingManager:
    """Enhanced training manager with metrics and analysis"""

    def __init__(
        self,
        config: TrainingConfig,
        save_dir: str = "models",
        experiment_name: str = None,
    ):
        self.config = config
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        # Initialize components
        self.logger = TrainingLogger(log_dir="logs", experiment_name=experiment_name)
        self.analyzer = PerformanceAnalyzer()

        # Save configuration
        config_path = os.path.join(save_dir, "training_config.json")
        config.save(config_path)

    def create_neural_players(self) -> List[NeuralPlayer]:
        """Create four neural network players with config"""
        winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
        players = []

        for i in range(4):
            player = NeuralPlayer(
                f"AI_Player_{i+1}", winds[i], learning_rate=self.config.learning_rate
            )

            # Apply configuration
            player.batch_size = self.config.batch_size
            player.memory = player.memory.__class__(maxlen=self.config.memory_size)
            player.epsilon = self.config.epsilon_start
            player.epsilon_min = self.config.epsilon_min
            player.epsilon_decay = self.config.epsilon_decay
            player.target_update_freq = self.config.target_update_freq

            players.append(player)

        return players

    def train_players(self):
        """Train neural network players with enhanced monitoring"""
        self.logger.logger.info(
            f"Starting enhanced training for {self.config.num_games} games"
        )

        # Create players
        neural_players = self.create_neural_players()

        # Load existing models if available
        for i, player in enumerate(neural_players):
            model_path = os.path.join(self.save_dir, f"player_{i+1}_model.pth")
            if os.path.exists(model_path):
                player.load_model(model_path)
                self.logger.logger.info(f"Loaded existing model for {player.name}")

        # Training loop
        for game_num in range(self.config.num_games):
            if (game_num + 1) % 50 == 0:
                self.logger.logger.info(f"Game {game_num + 1}/{self.config.num_games}")

            # Play game
            result = self.play_training_game(neural_players)

            # Collect player statistics
            player_stats = [player.get_stats() for player in neural_players]

            # Log and analyze results
            self.logger.log_game_result(game_num + 1, result, player_stats)
            self.analyzer.add_game_result(result, player_stats)

            # Save models periodically
            if (game_num + 1) % self.config.save_interval == 0:
                self.save_all_models(neural_players)
                self.logger.save_stats()

                # Log milestone
                milestone_stats = self.get_milestone_stats(neural_players)
                self.logger.log_training_milestone(
                    f"Game {game_num + 1}", milestone_stats
                )

            # Run evaluation periodically
            if (game_num + 1) % self.config.eval_interval == 0:
                eval_stats = self.evaluate_players(neural_players)
                self.logger.log_evaluation_results(eval_stats)

                # Plot learning curves
                plot_path = os.path.join(
                    self.save_dir, f"learning_curves_game_{game_num + 1}.png"
                )
                self.analyzer.plot_learning_curves(save_path=plot_path)

        # Final save and analysis
        self.save_all_models(neural_players)
        self.logger.save_stats()

        # Generate final report
        final_report = self.analyzer.generate_report()
        self.logger.logger.info(f"\n{final_report}")

        # Save final analysis
        report_path = os.path.join(self.save_dir, "final_training_report.txt")
        with open(report_path, "w") as f:
            f.write(final_report)

        # Final learning curves
        final_plot_path = os.path.join(self.save_dir, "final_learning_curves.png")
        self.analyzer.plot_learning_curves(save_path=final_plot_path)

        self.logger.logger.info("Enhanced training completed!")

    def play_training_game(self, players: List[NeuralPlayer]) -> Dict[str, Any]:
        """Play a single training game with enhanced reward system"""
        # Create game
        player_names = [p.name for p in players]
        game = MahjongEngine(player_names)
        for i, neural_player in enumerate(players):
            # Copy over the dealt hand and other state
            neural_player.hand = game.players[i].hand
            neural_player.score = game.players[i].score
            neural_player.seat_wind = game.players[i].seat_wind
            neural_player.is_dealer = game.players[i].is_dealer

        # Now replace the players
        game.players = players

        max_turns = 200
        turn_count = 0

        while game.phase.value != "ended" and turn_count < max_turns:
            current_player_idx = game.current_player
            current_player = players[current_player_idx]

            # Get game state and player hand
            game_state = game.get_game_state()
            player_hand = game.get_player_hand(current_player_idx)
            valid_actions = game.get_valid_actions(current_player_idx)

            # Debug check for empty actions
            if not valid_actions:
                print(f"ERROR: No valid actions for player {current_player_idx}")
                print(f"Hand size: {len(current_player.hand.concealed_tiles)}")
                print(f"Is current player: {current_player_idx == game.current_player}")
                print(f"Last discard: {game.last_discard}")
                print(f"Wall remaining: {game.wall.tiles_remaining()}")
                break

            # Player chooses action
            action, kwargs = current_player.choose_action(
                game_state, player_hand, valid_actions
            )
            # Execute action
            result = game.execute_action(current_player_idx, action, **kwargs)

            # Give enhanced reward based on action result
            if result["success"]:
                reward = self.calculate_enhanced_reward(
                    action, result, player_hand, game_state
                )
                current_player.give_reward(reward)
            else:
                current_player.give_reward(self.config.invalid_action_penalty)
                print(
                    f"Invalid action: {action} by player {current_player_idx} - {result['message']}"
                )

            # Check if game ended
            if result.get("game_ended", False):
                winner_idx = result.get("winner")
                final_scores = [p.score for p in game.players]

                # Give final rewards with enhanced scoring
                for i, player in enumerate(players):
                    won = i == winner_idx
                    final_reward = self.calculate_final_reward(
                        won, final_scores[i], result
                    )
                    player.update_game_result(won, final_scores[i])

                break

            # Simple turn advancement - only advance if it was a discard and no calls
            if action == "discard" and game.last_discard is not None:
                # Let other players respond in next iterations
                pass
            elif action == "pass":
                # Continue to next player who might want to call
                pass
            elif action in ["chii", "pon", "kan"]:
                # Caller becomes current player (handled in execute_action)
                game.last_discard = None  # Clear the discard

            # Check if we should advance turn (no pending calls)
            if self._should_advance_turn(game, action):
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
            "yaku": result.get("yaku", []),
            "score": result.get("score", 0),
        }

    def _should_advance_turn(self, game, last_action):
        """Determine if turn should advance"""
        # Advance turn after discard if no one can call
        if last_action == "discard" and game.last_discard is not None:
            # Check if any other player can call
            for i in range(4):
                if i != game.current_player:
                    actions = game.get_valid_actions(i)
                    if any(action != "pass" for action in actions):
                        return False  # Someone can call, don't advance
            return True  # No one can call, advance turn

        return False

    def calculate_enhanced_reward(
        self,
        action: str,
        result: Dict[str, Any],
        player_hand: Dict[str, Any],
        game_state: Dict[str, Any],
    ) -> float:
        """Calculate enhanced reward based on game context with progress incentives"""

        # Winning actions get maximum reward
        if action == "tsumo" or action == "ron":
            return self.config.win_reward

        elif action == "riichi":
            # Bonus for riichi based on hand quality
            winning_tiles = len(player_hand.get("winning_tiles", []))
            riichi_bonus = winning_tiles * 0.5  # More waits = better riichi
            return self.config.riichi_reward + riichi_bonus

        elif action == "discard":
            # Get hand analysis
            is_tenpai = player_hand.get("is_tenpai", False)
            winning_tiles = len(player_hand.get("winning_tiles", []))
            concealed_tiles = len(player_hand.get("concealed_tiles", []))

            # Reward structure based on hand progress
            if is_tenpai:
                # Strong reward for maintaining tenpai
                tenpai_bonus = winning_tiles * 0.3  # More waits = better
                return self.config.tenpai_reward + tenpai_bonus

            elif winning_tiles > 0:
                # Reward for being close to tenpai (1-shanten, 2-shanten, etc.)
                # More winning tiles = closer to tenpai = better reward
                progress_reward = self.config.base_reward * (1 + winning_tiles * 0.2)
                return progress_reward

            else:
                # Small penalty for having no clear path to winning
                # Encourage players to work toward tenpai
                stagnation_penalty = self.config.base_reward * 0.3
                return -stagnation_penalty

        elif action in ["chii", "pon", "kan"]:
            # Analyze if the call improves the hand
            winning_tiles = len(player_hand.get("winning_tiles", []))

            if winning_tiles > 0:
                # Good call that maintains winning potential
                call_bonus = self.config.base_reward * (2 + winning_tiles * 0.1)
                return call_bonus
            else:
                # Call that doesn't help winning - small penalty
                return self.config.base_reward * 0.5

        elif action == "pass":
            # Small reward for passing when appropriate
            # (avoiding bad calls is good strategy)
            return self.config.base_reward * 0.1

        # Default small reward for valid actions
        return self.config.base_reward * 0.5

    def calculate_final_reward(
        self, won: bool, final_score: int, result: Dict[str, Any]
    ) -> float:
        """Calculate final game reward with bonuses but no draw penalties"""

        if won:
            # Victory rewards
            base_reward = self.config.win_reward

            # Bonus for high-scoring wins
            score_bonus = result.get("score", 0) / 1000.0

            # Bonus for multiple yaku (skillful play)
            yaku_bonus = len(result.get("yaku", [])) * 1.0

            # Bonus for winning method
            win_method_bonus = 0
            if result.get("yaku"):
                # Check for special yaku that indicate good play
                yaku_names = [y.get("name", "") for y in result.get("yaku", [])]
                if "riichi" in yaku_names:
                    win_method_bonus += 2.0
                if "tanyao" in yaku_names or "pinfu" in yaku_names:
                    win_method_bonus += 1.0

            return base_reward + score_bonus + yaku_bonus + win_method_bonus

        else:
            # Loss handling without draw penalties
            winner = result.get("winner", -1)

            if winner == -1:
                # Game ended in draw - neutral outcome
                # Small bonus if player was tenpai at end
                tenpai_players = result.get("tenpai_players", [])
                player_index = result.get("player_index", -1)  # Would need to pass this

                if player_index in tenpai_players:
                    # Small reward for being tenpai in draw
                    return 2.0
                else:
                    # Neutral for not being tenpai in draw
                    return 0.0

            else:
                # Someone else won - small penalty based on placement
                base_penalty = -3.0

                # Less penalty if you placed well
                final_position = self._calculate_position(
                    final_score, result.get("final_scores", [])
                )
                position_adjustment = (
                    4 - final_position
                ) * 1.0  # 2nd place gets +2, 3rd gets +1

                # Score-based adjustment
                score_diff = final_score - 25000
                score_adjustment = score_diff / 5000.0

                return base_penalty + position_adjustment + score_adjustment

    def _calculate_position(self, player_score: int, all_scores: List[int]) -> int:
        """Calculate player's final position (1st, 2nd, 3rd, 4th)"""
        sorted_scores = sorted(all_scores, reverse=True)
        try:
            return sorted_scores.index(player_score) + 1
        except ValueError:
            return 4  # Default to last place if not found

    # Additional method to track and reward progress during game
    def give_progress_reward(
        self, player, previous_hand_state: Dict, current_hand_state: Dict
    ):
        """Give additional rewards for hand improvement during the game"""

        prev_winning_tiles = len(previous_hand_state.get("winning_tiles", []))
        curr_winning_tiles = len(current_hand_state.get("winning_tiles", []))

        prev_tenpai = previous_hand_state.get("is_tenpai", False)
        curr_tenpai = current_hand_state.get("is_tenpai", False)

        # Reward for achieving tenpai
        if not prev_tenpai and curr_tenpai:
            player.give_reward(3.0)

        # Reward for improving winning tile count
        elif curr_winning_tiles > prev_winning_tiles:
            improvement_reward = (curr_winning_tiles - prev_winning_tiles) * 0.5
            player.give_reward(improvement_reward)

        # Small penalty for getting further from tenpai
        elif curr_winning_tiles < prev_winning_tiles:
            regression_penalty = (prev_winning_tiles - curr_winning_tiles) * -0.3
            player.give_reward(regression_penalty)

    def get_milestone_stats(self, players: List[NeuralPlayer]) -> Dict[str, Any]:
        """Get milestone statistics"""
        stats = {}
        for i, player in enumerate(players):
            player_stats = player.get_stats()
            stats[f"player_{i+1}"] = {
                "win_rate": player_stats["win_rate"],
                "epsilon": player_stats["epsilon"],
                "memory_size": player_stats["memory_size"],
                "avg_loss": player_stats["avg_recent_loss"],
            }
        return stats

    def save_all_models(self, players: List[NeuralPlayer]):
        """Save all player models"""
        for i, player in enumerate(players):
            model_path = os.path.join(self.save_dir, f"player_{i+1}_model.pth")
            player.save_model(model_path)

    def evaluate_players(self, players: List[NeuralPlayer]) -> Dict[str, Any]:
        """Evaluate players with no exploration"""
        # Save current epsilon values
        original_epsilons = [p.epsilon for p in players]

        # Set epsilon to 0 for evaluation
        for player in players:
            player.epsilon = 0.0

        eval_results = []

        for game_num in range(self.config.eval_games):
            result = self.play_training_game(players)
            eval_results.append(result)

        # Restore original epsilon values
        for player, epsilon in zip(players, original_epsilons):
            player.epsilon = epsilon

        # Calculate evaluation statistics
        wins = [0] * 4
        total_scores = [0] * 4

        for result in eval_results:
            winner = result["winner"]
            if winner >= 0:
                wins[winner] += 1

            for i, score in enumerate(result["final_scores"]):
                total_scores[i] += score

        num_games = len(eval_results)
        win_rates = [w / num_games for w in wins]
        avg_scores = [s / num_games for s in total_scores]

        return {
            "win_rates": win_rates,
            "avg_scores": avg_scores,
            "total_games": num_games,
            "wins": wins,
        }
