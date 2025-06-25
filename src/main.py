#!/usr/bin/env python3
"""
Main entry point for Riichi Mahjong Engine
"""

from game.engine import MahjongEngine
import json

def main():
    """Main game loop for testing"""
    print("Starting Riichi Mahjong Engine...")
    
    # Create game with 4 players
    player_names = ["Player 1", "Player 2", "Player 3", "Player 4"]
    game = MahjongEngine(player_names)
    
    print("Game initialized!")
    print(json.dumps(game.get_game_state(), indent=2))
    
    # Example: Show first player's hand
    print("\nPlayer 1's hand:")
    print(json.dumps(game.get_player_hand(0), indent=2))
    
    print("\nValid actions for Player 1:")
    print(game.get_valid_actions(0))

if __name__ == "__main__":
    main()
