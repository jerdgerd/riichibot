import random
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from game.engine import GameAction
from game.player import Player
from tiles.tile import Tile


class MahjongNet(nn.Module):
    """Neural network for Mahjong decision making"""

    def __init__(self, input_size: int = 400, hidden_size: int = 512):
        super(MahjongNet, self).__init__()

        # Feature extraction layers
        self.feature_net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, 256),
            nn.ReLU(),
        )

        # Action value heads
        self.discard_head = nn.Linear(256, 34)  # 34 possible tile types
        self.call_head = nn.Linear(256, 4)  # chii, pon, kan, pass
        self.riichi_head = nn.Linear(256, 2)  # riichi or not
        self.win_head = nn.Linear(256, 2)  # ron/tsumo or not

    def forward(self, x):
        features = self.feature_net(x)

        return {
            "discard": self.discard_head(features),
            "call": self.call_head(features),
            "riichi": self.riichi_head(features),
            "win": self.win_head(features),
        }


class NeuralPlayer(Player):
    """AI Player using neural network for decision making"""

    def __init__(self, name: str, seat_wind, learning_rate: float = 0.001):
        super().__init__(name, seat_wind)

        # Neural network
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.net = MahjongNet().to(self.device)
        self.target_net = MahjongNet().to(self.device)  # Target network for stability
        self.optimizer = optim.Adam(self.net.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()

        # Copy weights to target network
        self.target_net.load_state_dict(self.net.state_dict())

        # Experience replay
        self.memory = deque(maxlen=10000)
        self.batch_size = 32

        # Exploration parameters
        self.epsilon = 1.0  # Start with full exploration
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995

        # Training tracking
        self.total_games = 0
        self.wins = 0
        self.losses = []
        self.last_state = None
        self.last_action = None
        self.target_update_freq = 100
        self.training_step = 0

    def encode_game_state(
        self, game_state: Dict[str, Any], player_hand: Dict[str, Any]
    ) -> torch.Tensor:
        """Encode game state into neural network input"""
        features = []

        # Hand encoding (34 tile types * 4 copies = 136 features)
        hand_encoding = [0] * 136
        for tile_str in player_hand["concealed_tiles"]:
            tile_idx = self._tile_to_index(tile_str)
            if tile_idx < 136:
                hand_encoding[tile_idx] += 1

        # Meld encoding
        meld_encoding = [0] * 34
        for meld in player_hand["melds"]:
            if meld["tiles"]:
                tile_idx = self._tile_to_index(meld["tiles"][0])
                if tile_idx < 34:
                    meld_encoding[tile_idx] = 1

        # Game context
        context = [
            game_state["current_player"] / 3.0,  # Normalize
            game_state["dealer"] / 3.0,
            game_state["round_number"] / 4.0,
            game_state["wall_tiles_remaining"] / 70.0,
            len(game_state["dora_indicators"]) / 4.0,
            1.0 if player_hand["is_tenpai"] else 0.0,
            1.0 if player_hand["can_riichi"] else 0.0,
        ]

        # Other players' info
        for i, p in enumerate(game_state["players"]):
            if i != self._get_player_index(game_state):
                context.extend(
                    [
                        p["score"] / 50000.0,  # Normalize score
                        p["hand_size"] / 14.0,
                        p["melds"] / 4.0,
                        len(p["discards"]) / 20.0,
                        1.0 if p["is_riichi"] else 0.0,
                        1.0 if p["is_tenpai"] else 0.0,
                        1.0 if p["is_dealer"] else 0.0,
                    ]
                )

        # Pad context to fixed size
        while len(context) < 100:
            context.append(0.0)

        # Combine all features
        features = hand_encoding + meld_encoding + context

        # Pad to input size
        while len(features) < 400:
            features.append(0.0)

        return torch.FloatTensor(features[:400]).to(self.device)

    def _tile_to_index(self, tile_str: str) -> int:
        """Convert tile string to index (0-33)"""
        tile_map = {}
        idx = 0

        # Number tiles
        for suit in ["sou", "pin", "man"]:
            for value in range(1, 10):
                tile_map[f"{value}{suit}"] = idx
                idx += 1

        # Honor tiles
        for wind in ["east", "south", "west", "north"]:
            tile_map[wind] = idx
            idx += 1

        for dragon in ["white", "green", "red"]:
            tile_map[dragon] = idx
            idx += 1

        return tile_map.get(tile_str, 0)

    def _get_player_index(self, game_state: Dict[str, Any]) -> int:
        """Get this player's index in the game"""
        for i, p in enumerate(game_state["players"]):
            if p["name"] == self.name:
                return i
        return 0

    def choose_action(
        self,
        game_state: Dict[str, Any],
        player_hand: Dict[str, Any],
        valid_actions: List[str],
    ) -> Tuple[str, Dict[str, Any]]:
        """Choose action using neural network"""

        # Encode state
        state_tensor = self.encode_game_state(game_state, player_hand)

        # Store current state for learning
        self.last_state = state_tensor

        # Get action probabilities
        with torch.no_grad():
            action_values = self.net(state_tensor.unsqueeze(0))

        # Epsilon-greedy exploration
        if random.random() < self.epsilon:
            action = random.choice(valid_actions)
            kwargs = self._get_random_action_kwargs(action, player_hand)
        else:
            action, kwargs = self._select_best_action(
                action_values, valid_actions, player_hand
            )

        self.last_action = (action, kwargs)
        return action, kwargs

    def _select_best_action(
        self,
        action_values: Dict[str, torch.Tensor],
        valid_actions: List[str],
        player_hand: Dict[str, Any],
    ) -> Tuple[str, Dict[str, Any]]:
        """Select best action from neural network output"""

        best_action = "pass"
        best_kwargs = {}
        best_score = float("-inf")

        for action in valid_actions:
            if action == "discard":
                # Get best tile to discard
                discard_values = action_values["discard"].squeeze()
                available_tiles = player_hand["concealed_tiles"]

                best_tile_score = float("-inf")
                best_tile = None

                for tile_str in available_tiles:
                    tile_idx = self._tile_to_index(tile_str)
                    if tile_idx < len(discard_values):
                        score = discard_values[tile_idx].item()
                        if score > best_tile_score:
                            best_tile_score = score
                            best_tile = tile_str

                if best_tile and best_tile_score > best_score:
                    best_score = best_tile_score
                    best_action = "discard"
                    best_kwargs = {"tile": best_tile}

            elif action == "riichi":
                riichi_score = action_values["riichi"].squeeze()[1].item()
                if riichi_score > best_score:
                    best_score = riichi_score
                    best_action = "riichi"
                    if player_hand["concealed_tiles"]:
                        best_kwargs = {"tile": player_hand["concealed_tiles"][0]}

            elif action in ["ron", "tsumo"]:
                win_score = action_values["win"].squeeze()[1].item()
                if win_score > best_score:
                    best_score = win_score
                    best_action = action
                    best_kwargs = {}

            elif action in ["chii", "pon", "kan"]:
                call_idx = {"chii": 0, "pon": 1, "kan": 2}.get(action, 3)
                call_score = action_values["call"].squeeze()[call_idx].item()
                if call_score > best_score:
                    best_score = call_score
                    best_action = action
                    best_kwargs = self._get_call_kwargs(action, player_hand)

        return best_action, best_kwargs

    def _get_random_action_kwargs(
        self, action: str, player_hand: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get random kwargs for action"""
        if action == "discard":
            if player_hand["concealed_tiles"]:
                return {"tile": random.choice(player_hand["concealed_tiles"])}
        elif action == "riichi":
            if player_hand["concealed_tiles"]:
                return {"tile": random.choice(player_hand["concealed_tiles"])}
        elif action == "chii":
            return {"sequence": []}

        return {}

    def _get_call_kwargs(
        self, action: str, player_hand: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get kwargs for call actions"""
        if action == "chii":
            return {"sequence": []}
        return {}

    def remember(
        self,
        state: torch.Tensor,
        action: str,
        reward: float,
        next_state: torch.Tensor,
        done: bool,
    ):
        """Store experience in replay buffer"""
        self.memory.append((state, action, reward, next_state, done))

    def give_reward(
        self, reward: float, next_state: torch.Tensor = None, done: bool = False
    ):
        """Give reward for the last action taken"""
        if self.last_state is not None and self.last_action is not None:
            if next_state is None:
                next_state = torch.zeros_like(self.last_state)

            self.remember(
                self.last_state, self.last_action[0], reward, next_state, done
            )

            # Train if we have enough experiences
            if len(self.memory) >= self.batch_size:
                self.replay_training()

    def replay_training(self):
        """Train the network using experience replay"""
        if len(self.memory) < self.batch_size:
            return

        batch = random.sample(self.memory, self.batch_size)
        states = torch.stack([exp[0] for exp in batch])
        actions = [exp[1] for exp in batch]
        rewards = torch.FloatTensor([exp[2] for exp in batch]).to(self.device)
        next_states = torch.stack([exp[3] for exp in batch])
        dones = torch.BoolTensor([exp[4] for exp in batch]).to(self.device)

        current_q_values = self.net(states)
        next_q_values = self.target_net(next_states)

        # Calculate target Q-values
        gamma = 0.99  # Discount factor
        target_q_values = {}

        for head_name in current_q_values.keys():
            target_q_values[head_name] = rewards.clone()

            # Add discounted future rewards for non-terminal states
            non_terminal_mask = ~dones
            if non_terminal_mask.any():
                max_next_q = next_q_values[head_name][non_terminal_mask].max(1)[0]
                target_q_values[head_name][non_terminal_mask] += gamma * max_next_q

        # Calculate loss for each head
        total_loss = torch.tensor(
            0.0, device=self.device, requires_grad=True
        )  # Fix: Initialize as tensor

        for head_name in current_q_values.keys():
            # Create action mask for this head
            action_mask = torch.zeros(
                len(actions), current_q_values[head_name].size(1)
            ).to(self.device)

            for i, action in enumerate(actions):
                if head_name == "discard" and action == "discard":
                    # For discard, we need to know which tile was discarded
                    # For simplicity, use index 0 (this could be improved)
                    action_mask[i, 0] = 1
                elif head_name == "call" and action in ["chii", "pon", "kan"]:
                    action_idx = {"chii": 0, "pon": 1, "kan": 2}.get(action, 3)
                    if action_idx < current_q_values[head_name].size(1):  # Safety check
                        action_mask[i, action_idx] = 1
                elif head_name == "riichi" and action == "riichi":
                    action_mask[i, 1] = 1
                elif head_name == "win" and action in ["ron", "tsumo"]:
                    action_mask[i, 1] = 1

            # Calculate Q-values for taken actions
            current_q = (current_q_values[head_name] * action_mask).sum(1)
            target_q = target_q_values[head_name]

            # Only calculate loss where actions were taken
            mask = action_mask.sum(1) > 0
            if mask.any():
                loss = self.criterion(current_q[mask], target_q[mask])
                total_loss = total_loss + loss  # Fix: Use tensor addition

        # Only backpropagate if we have a valid loss
        if total_loss.requires_grad and total_loss.item() > 0:
            # Backpropagation
            self.optimizer.zero_grad()
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.net.parameters(), 1.0)
            self.optimizer.step()

            # Track loss
            self.losses.append(total_loss.item())

        # Update target network periodically
        self.training_step += 1
        if self.training_step % self.target_update_freq == 0:
            self.target_net.load_state_dict(self.net.state_dict())

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def update_game_result(self, won: bool, final_score: int):
        """Update statistics after game ends"""
        self.total_games += 1
        if won:
            self.wins += 1
            reward = 10.0 + (final_score - 25000) / 1000.0  # Base reward + score bonus
        else:
            reward = -5.0 + (final_score - 25000) / 2000.0  # Penalty + score adjustment

        # Give final reward
        self.give_reward(reward, done=True)

    def save_model(self, filepath: str):
        """Save the neural network model"""
        torch.save(
            {
                "model_state_dict": self.net.state_dict(),
                "target_model_state_dict": self.target_net.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "epsilon": self.epsilon,
                "total_games": self.total_games,
                "wins": self.wins,
                "training_step": self.training_step,
            },
            filepath,
        )

    def load_model(self, filepath: str):
        """Load a saved neural network model"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.net.load_state_dict(checkpoint["model_state_dict"])
        self.target_net.load_state_dict(checkpoint["target_model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.epsilon = checkpoint.get("epsilon", self.epsilon)
        self.total_games = checkpoint.get("total_games", 0)
        self.wins = checkpoint.get("wins", 0)
        self.training_step = checkpoint.get("training_step", 0)

    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics"""
        win_rate = self.wins / max(1, self.total_games)
        avg_loss = sum(self.losses[-100:]) / max(1, len(self.losses[-100:]))

        return {
            "total_games": self.total_games,
            "wins": self.wins,
            "win_rate": win_rate,
            "epsilon": self.epsilon,
            "avg_recent_loss": avg_loss,
            "memory_size": len(self.memory),
            "training_steps": self.training_step,
        }
