# src/ai/ai_game.py
"""
Interface for playing against trained AI players
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import List, Dict, Any
from game.engine import MahjongEngine
from game.player import Player
from ai.neural_player import NeuralPlayer
from tiles.tile import Wind
from utils.constants import format_hand_display

class HumanPlayer(Player):
    """Human player with console interface"""
    
    def choose_action(self, game_state: Dict[str, Any], 
                     player_hand: Dict[str, Any], 
                     valid_actions: List[str]) -> tuple:
        """Get action from human player via console"""
        
        print(f"\n{self.name}'s turn:")
        print(f"Your hand: {format_hand_display([tile for tile in self.hand.concealed_tiles])}")
        print(f"Score: {self.score}")
        
        if player_hand.get('is_tenpai', False):
            print("🎯 You are TENPAI!")
            winning_tiles = player_hand.get('winning_tiles', [])
            print(f"Winning tiles: {winning_tiles}")
        
        print(f"Valid actions: {valid_actions}")
        
        while True:
            try:
                action = input("Choose action: ").strip().lower()
                
                if action not in valid_actions:
                    print(f"Invalid action. Choose from: {valid_actions}")
                    continue
                
                kwargs = {}
                
                if action == "discard":
                    print("Available tiles:")
                    for i, tile_str in enumerate(player_hand['concealed_tiles']):
                        print(f"{i}: {tile_str}")
                    
                    tile_idx = int(input("Choose tile index to discard: "))
                    if 0 <= tile_idx < len(player_hand['concealed_tiles']):
                        kwargs['tile'] = player_hand['concealed_tiles'][tile_idx]
                    else:
                        print("Invalid tile index")
                        continue
                
                elif action == "riichi":
                    print("Available tiles to discard with riichi:")
                    for i, tile_str in enumerate(player_hand['concealed_tiles']):
                        print(f"{i}: {tile_str}")
                    
                    tile_idx = int(input("Choose tile index to discard: "))
                    if 0 <= tile_idx < len(player_hand['concealed_tiles']):
                        kwargs['tile'] = player_hand['concealed_tiles'][tile_idx]
                    else:
                        print("Invalid tile index")
                        continue
                
                return action, kwargs
                
            except (ValueError, IndexError):
                print("Invalid input. Please try again.")
            except KeyboardInterrupt:
                print("\nGame interrupted by user.")
                sys.exit(0)

class AIGameManager:
    """Manages games between human and AI players"""
    
    def __init__(self, model_dir: str = "models"):
        self.model_dir = model_dir
    
    def create_mixed_players(self, human_count: int = 1) -> List[Player]:
        """Create mix of human and AI players"""
        winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
        players = []
        
        # Create human players
        for i in range(human_count):
            player = HumanPlayer(f"Human_{i+1}", winds[i])
            players.append(player)
        
        # Create AI players
        for i in range(human_count, 4):
            ai_player = NeuralPlayer(f"AI_Player_{i+1}", winds[i])
            
            # Load trained model
            model_path = os.path.join(self.model_dir, f"player_{i+1}_model.pth")
            if os.path.exists(model_path):
                ai_player.load_model(model_path)
                ai_player.epsilon = 0.0  # No exploration in gameplay
                print(f"Loaded trained model for {ai_player.name}")
            else:
                print(f"No trained model found for {ai_player.name}, using random play")
            
            players.append(ai_player)
        
        return players
    
    def play_human_vs_ai(self, human_count: int = 1):
        """Play a game with human vs AI players"""
        print("Starting Human vs AI Mahjong Game!")
        print("="*50)
        
        # Create mixed players
        players = self.create_mixed_players(human_count)
        
        # Create game
        player_names = [p.name for p in players]
        game = MahjongEngine(player_names)
        game.players = players
        
        # Play the game
        self.run_interactive_game(game, players)
    
    def run_interactive_game(self, game: MahjongEngine, players: List[Player]):
        """Run an interactive game with display"""
        max_turns = 200
        turn_count = 0
        
        print("\nGame started!")
        self.display_game_state(game)
        
        while game.phase.value != "ended" and turn_count < max_turns:
            current_player_idx = game.current_player
            current_player = players[current_player_idx]
            
            # Get game state and player hand
            game_state = game.get_game_state()
            player_hand = game.get_player_hand(current_player_idx)
            valid_actions = game.get_valid_actions(current_player_idx)
            
            # Display current state for all players
            if not isinstance(current_player, HumanPlayer):
                print(f"\n{current_player.name}'s turn (AI)")
                print(f"Hand size: {len(current_player.hand.concealed_tiles)}")
                print(f"Score: {current_player.score}")
            
            # Player chooses action
            if isinstance(current_player, HumanPlayer):
                action, kwargs = current_player.choose_action(game_state, player_hand, valid_actions)
            else:
                action, kwargs = current_player.choose_action(game_state, player_hand, valid_actions)
                print(f"AI chose: {action} {kwargs}")
            
            # Execute action
            result = game.execute_action(current_player_idx, action, **kwargs)
            
            if not result["success"]:
                print(f"Action failed: {result['message']}")
                continue
            
            # Display result
            if action == "discard":
                print(f"{current_player.name} discarded {kwargs.get('tile', 'unknown')}")
            elif action in ["ron", "tsumo"]:
                print(f"🎉 {current_player.name} won by {action}!")
            elif action == "riichi":
                print(f"🔥 {current_player.name} declared RIICHI!")
            
            # Check if game ended
            if result.get("game_ended", False):
                self.display_game_end(result, players)
                break
            
            # Advance turn if no calls were made
            if game.last_discard is None:
                game.advance_turn()
            
            # Display updated state
            self.display_game_state(game)
            
            turn_count += 1
        
        if turn_count >= max_turns:
            print("Game ended due to turn limit (draw)")
    
    def display_game_state(self, game: MahjongEngine):
        """Display current game state"""
        state = game.get_game_state()
        
        print(f"\n--- Round {state['round_number']} ({state['round_wind']}) ---")
        print(f"Current Player: {state['players'][state['current_player']]['name']}")
        print(f"Wall tiles remaining: {state['wall_tiles_remaining']}")
        print(f"Dora indicators: {state['dora_indicators']}")
        
        if state.get('last_discard'):
            print(f"Last discard: {state['last_discard']}")
        
        # Show player scores and status
        print("\nPlayer Status:")
        for i, p in enumerate(state['players']):
            status = []
            if p['is_dealer']:
                status.append("DEALER")
            if p['is_riichi']:
                status.append("RIICHI")
            if p['is_tenpai']:
                status.append("TENPAI")
            
            status_str = f" ({', '.join(status)})" if status else ""
            print(f"  {p['name']}: {p['score']} points{status_str}")
    
    def display_game_end(self, result: Dict[str, Any], players: List[Player]):
        """Display game end results"""
        print("\n" + "="*50)
        print("GAME ENDED!")
        print("="*50)
        
        if result.get('winner', -1) >= 0:
            winner = players[result['winner']]
            print(f"🏆 Winner: {winner.name}")
            print(f"Score: {result.get('score', 0)} points")
            
            if 'yaku' in result:
                print("Yaku:")
                for yaku in result['yaku']:
                    print(f"  - {yaku['name']}: {yaku['han']} han")
        else:
            print("Game ended in a draw")
        
        print("\nFinal Scores:")
        for i, player in enumerate(players):
            print(f"  {player.name}: {player.score} points")

def main():
    """Main function for human vs AI gameplay"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Play Mahjong against AI')
    parser.add_argument('--model-dir', type=str, default='models',
                       help='Directory containing trained models')
    parser.add_argument('--humans', type=int, default=1, choices=[1, 2, 3],
                       help='Number of human players (1-3)')
    
    args = parser.parse_args()
    
    # Create game manager
    game_manager = AIGameManager(model_dir=args.model_dir)
    
    # Play game
    game_manager.play_human_vs_ai(human_count=args.humans)

if __name__ == "__main__":
    main()
