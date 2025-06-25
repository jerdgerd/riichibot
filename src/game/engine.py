from typing import List, Optional, Dict, Any
from enum import Enum 
import random
from game.player import Player
from game.hand import Hand, Meld
from game.rules import YakuChecker
from game.scoring import Scoring
from tiles.tile import Tile, Wind
from tiles.wall import Wall

class GamePhase(Enum):
    DEALING = "dealing"
    PLAYING = "playing"
    ENDED = "ended"

class GameAction(Enum):
    DRAW = "draw"
    DISCARD = "discard"
    CHII = "chii"
    PON = "pon"
    KAN = "kan"
    RIICHI = "riichi"
    RON = "ron"
    TSUMO = "tsumo"
    PASS = "pass"

class MahjongEngine:
    """Main game engine for Riichi Mahjong"""

    def __init__(self, player_names: List[str], use_red_fives: bool = True):
        if len(player_names) != 4:
            raise ValueError("Exactly 4 players required")
        
        self.players: List[Player] = []
        self.wall = Wall(use_red_fives)
        self.current_player = 0
        self.dealer = 0
        self.round_wind = Wind.EAST
        self.round_number = 1
        self.turn_number = 0
        self.phase = GamePhase.DEALING
        self.last_discard: Optional[Tile] = None
        self.last_discard_player: Optional[int] = None
        self.riichi_bets = 0
        self.honba = 0  # Bonus counters
        
        # Initialize players
        winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
        for i, name in enumerate(player_names):
            player = Player(name, winds[i])
            if i == 0:
                player.is_dealer = True
            self.players.append(player)
        
        self._deal_initial_hands()

    def _deal_initial_hands(self):
        """Deal 13 tiles to each player"""
        for _ in range(13):
            for player in self.players:
                tile = self.wall.draw_tile()
                player.draw_tile(tile)
        
        # Dealer draws 14th tile
        self.players[self.dealer].draw_tile(self.wall.draw_tile())
        self.phase = GamePhase.PLAYING

    def get_game_state(self) -> Dict[str, Any]:
        """Get current game state"""
        return {
            "phase": self.phase.value,
            "current_player": self.current_player,
            "dealer": self.dealer,
            "round_wind": self.round_wind.value,
            "round_number": self.round_number,
            "turn_number": self.turn_number,
            "wall_tiles_remaining": self.wall.tiles_remaining(),
            "dora_indicators": [str(tile) for tile in self.wall.dora_indicators],
            "last_discard": str(self.last_discard) if self.last_discard else None,
            "riichi_bets": self.riichi_bets,
            "players": [
                {
                    "name": p.name,
                    "score": p.score,
                    "seat_wind": p.seat_wind.value,
                    "is_dealer": p.is_dealer,
                    "is_riichi": p.hand.is_riichi,
                    "hand_size": len(p.hand.concealed_tiles),
                    "melds": len(p.hand.melds),
                    "discards": [str(tile) for tile in p.hand.discards],
                    "is_tenpai": p.is_tenpai()
                }
                for p in self.players
            ]
        }

    def get_player_hand(self, player_index: int) -> Dict[str, Any]:
        """Get specific player's hand information"""
        player = self.players[player_index]
        return {
            "concealed_tiles": [str(tile) for tile in player.hand.concealed_tiles],
            "melds": [
                {
                    "tiles": [str(tile) for tile in meld.tiles],
                    "type": meld.meld_type,
                    "is_open": meld.is_open
                }
                for meld in player.hand.melds
            ],
            "winning_tiles": [str(tile) for tile in player.hand.get_winning_tiles()],
            "is_tenpai": player.is_tenpai(),
            "can_riichi": self._can_declare_riichi(player_index)
        }

    def get_valid_actions(self, player_index: int) -> List[str]:
        """Get valid actions for a player"""
        player = self.players[player_index]
        actions = []
        
        if self.current_player == player_index:
            # Current player's turn
            if len(player.hand.concealed_tiles) == 14:
                actions.append("discard")
                if player.can_tsumo():
                    actions.append("tsumo")
                if self._can_declare_riichi(player_index):
                    actions.append("riichi")
        else:
            # Other players can call discards
            if self.last_discard:
                if player.can_call_ron(self.last_discard):
                    actions.append("ron")
                if player.can_call_pon(self.last_discard):
                    actions.append("pon")
                if player.can_call_kan(self.last_discard):
                    actions.append("kan")
                
                # Chii only from left player
                if (self.last_discard_player + 1) % 4 == player_index:
                    if player.can_call_chii(self.last_discard, True):
                        actions.append("chii")
        
        actions.append("pass")
        return actions

    def execute_action(self, player_index: int, action: str, **kwargs) -> Dict[str, Any]:
        """Execute a player action"""
        result = {"success": False, "message": "", "game_ended": False}
        
        try:
            if action == "discard":
                tile_str = kwargs.get("tile")
                result = self._execute_discard(player_index, tile_str)
            
            elif action == "tsumo":
                result = self._execute_tsumo(player_index)
            
            elif action == "ron":
                result = self._execute_ron(player_index)
            
            elif action == "riichi":
                tile_str = kwargs.get("tile")
                result = self._execute_riichi(player_index, tile_str)
            
            elif action == "chii":
                sequence = kwargs.get("sequence", [])
                result = self._execute_chii(player_index, sequence)
            
            elif action == "pon":
                result = self._execute_pon(player_index)
            
            elif action == "kan":
                result = self._execute_kan(player_index)
            
            elif action == "pass":
                result = {"success": True, "message": "Passed"}
            
            else:
                result["message"] = f"Unknown action: {action}"
            
            # Check if wall is empty
            if self.wall.tiles_remaining() == 0 and not result.get("game_ended"):
                result = self._handle_draw()
            
        except Exception as e:
            result["message"] = str(e)
        
        return result

    def _execute_discard(self, player_index: int, tile_str: str) -> Dict[str, Any]:
        """Execute discard action"""
        if player_index != self.current_player:
            return {"success": False, "message": "Not your turn"}
        
        player = self.players[player_index]
        
        # Find tile to discard
        tile_to_discard = None
        for tile in player.hand.concealed_tiles:
            if str(tile) == tile_str:
                tile_to_discard = tile
                break
        
        if not tile_to_discard:
            return {"success": False, "message": "Tile not found in hand"}
        
        # Execute discard
        discarded_tile = player.discard_tile(tile_to_discard)
        self.last_discard = discarded_tile
        self.last_discard_player = player_index
        
        # Check furiten for all players
        all_discards = [p.hand.discards for p in self.players]
        for p in self.players:
            p.hand.check_furiten(all_discards)
        
        return {"success": True, "message": f"Discarded {discarded_tile}"}

    def _execute_tsumo(self, player_index: int) -> Dict[str, Any]:
        """Execute tsumo (self-draw win)"""
        player = self.players[player_index]
        
        if not player.can_tsumo():
            return {"success": False, "message": "Cannot tsumo"}
        
        # Calculate score
        winning_tile = player.hand.concealed_tiles[-1]  # Last drawn tile
        yaku_list = YakuChecker.check_all_yaku(
            player.hand, winning_tile, True, 
            player.seat_wind, self.round_wind,
            self.wall.get_dora_tiles(),
            self.wall.get_ura_dora_tiles() if player.hand.is_riichi else None
        )
        
        score, payments = Scoring.calculate_score(yaku_list, player.is_dealer, True)
        
        # Apply payments
        self._apply_tsumo_payments(player_index, score, payments)
        
        self.phase = GamePhase.ENDED
        
        return {
            "success": True, 
            "message": f"{player.name} won by tsumo!",
            "game_ended": True,
            "winner": player_index,
            "score": score,
            "yaku": [{"name": y.name, "han": y.han} for y in yaku_list]
        }

    def _execute_ron(self, player_index: int) -> Dict[str, Any]:
        """Execute ron (win on discard)"""
        player = self.players[player_index]
        
        if not self.last_discard or not player.can_call_ron(self.last_discard):
            return {"success": False, "message": "Cannot call ron"}
        
        # Calculate score
        yaku_list = YakuChecker.check_all_yaku(
            player.hand, self.last_discard, False,
            player.seat_wind, self.round_wind,
            self.wall.get_dora_tiles(),
            self.wall.get_ura_dora_tiles() if player.hand.is_riichi else None
        )
        
        score, payments = Scoring.calculate_score(yaku_list, player.is_dealer, False)
        
        # Apply payments
        discarder = self.players[self.last_discard_player]
        discarder.add_score(-score)
        player.add_score(score)
        
        # Add riichi bets
        player.add_score(self.riichi_bets * 1000)
        self.riichi_bets = 0
        
        self.phase = GamePhase.ENDED
        
        return {
            "success": True,
            "message": f"{player.name} won by ron!",
            "game_ended": True,
            "winner": player_index,
            "score": score,
            "yaku": [{"name": y.name, "han": y.han} for y in yaku_list]
        }

    def _execute_riichi(self, player_index: int, tile_str: str) -> Dict[str, Any]:
        """Execute riichi declaration"""
        if player_index != self.current_player:
            return {"success": False, "message": "Not your turn"}
        
        player = self.players[player_index]
        
        if not self._can_declare_riichi(player_index):
            return {"success": False, "message": "Cannot declare riichi"}
        
        # Find tile to discard
        tile_to_discard = None
        for tile in player.hand.concealed_tiles:
            if str(tile) == tile_str:
                tile_to_discard = tile
                break
        
        if not tile_to_discard:
            return {"success": False, "message": "Tile not found in hand"}
        
        # Declare riichi and discard
        player.declare_riichi(self.turn_number)
        self.riichi_bets += 1
        
        discarded_tile = player.discard_tile(tile_to_discard)
        self.last_discard = discarded_tile
        self.last_discard_player = player_index
        
        return {"success": True, "message": f"{player.name} declared riichi and discarded {discarded_tile}"}

    def _execute_chii(self, player_index: int, sequence: List[str]) -> Dict[str, Any]:
        """Execute chii call"""
        player = self.players[player_index]
        
        if not self.last_discard:
            return {"success": False, "message": "No tile to call"}
        
        # Check if player is to the right of discarder (can call chii)
        if (self.last_discard_player + 1) % 4 != player_index:
            return {"success": False, "message": "Can only chii from left player"}
        
        # Convert sequence strings to tiles
        sequence_tiles = []
        for tile_str in sequence:
            # Find matching tile in hand
            for tile in player.hand.concealed_tiles:
                if str(tile) == tile_str:
                    sequence_tiles.append(tile)
                    break
        
        if len(sequence_tiles) != 2:  # Need 2 tiles + called tile = 3
            return {"success": False, "message": "Invalid sequence"}
        
        # Execute chii
        full_sequence = sequence_tiles + [self.last_discard]
        full_sequence.sort(key=lambda t: t.value)
        
        player.call_chii(self.last_discard, full_sequence)
        self.current_player = player_index
        self.last_discard = None
        
        return {"success": True, "message": f"{player.name} called chii"}

    def _execute_pon(self, player_index: int) -> Dict[str, Any]:
        """Execute pon call"""
        player = self.players[player_index]
        
        if not self.last_discard or not player.can_call_pon(self.last_discard):
            return {"success": False, "message": "Cannot call pon"}
        
        player.call_pon(self.last_discard, self.last_discard_player)
        self.current_player = player_index
        self.last_discard = None
        
        return {"success": True, "message": f"{player.name} called pon"}

    def _execute_kan(self, player_index: int) -> Dict[str, Any]:
        """Execute kan call"""
        player = self.players[player_index]
        
        if self.last_discard:
            # Open kan from discard
            if not player.can_call_kan(self.last_discard):
                return {"success": False, "message": "Cannot call kan"}
            
            player.call_kan(self.last_discard, self.last_discard_player)
            self.current_player = player_index
            self.last_discard = None
        else:
            # Closed kan from hand
            # This would need additional logic to specify which tile to kan
            return {"success": False, "message": "Closed kan not implemented"}
        
        # Add new dora indicator
        self.wall.add_dora_indicator()
        
        # Player draws replacement tile
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
        
        return {"success": True, "message": f"{player.name} called kan"}

    def _can_declare_riichi(self, player_index: int) -> bool:
        """Check if player can declare riichi"""
        player = self.players[player_index]
        return (player.hand.is_closed() and 
                player.is_tenpai() and 
                player.score >= 1000 and
                not player.hand.is_riichi)

    def _apply_tsumo_payments(self, winner_index: int, score: int, payments: Dict[str, int]):
        """Apply tsumo payment distribution"""
        winner = self.players[winner_index]
        
        if winner.is_dealer:
            # All players pay equally
            payment = payments["all"]
            for i, player in enumerate(self.players):
                if i != winner_index:
                    player.add_score(-payment)
                    winner.add_score(payment)
        else:
            # Dealer pays half, others pay quarter
            dealer_payment = payments["dealer"]
            non_dealer_payment = payments["non_dealer"]
            
            for i, player in enumerate(self.players):
                if i == winner_index:
                    continue
                elif player.is_dealer:
                    player.add_score(-dealer_payment)
                    winner.add_score(dealer_payment)
                else:
                    player.add_score(-non_dealer_payment)
                    winner.add_score(non_dealer_payment)
        
        # Add riichi bets
        winner.add_score(self.riichi_bets * 1000)
        self.riichi_bets = 0

    def _handle_draw(self) -> Dict[str, Any]:
        """Handle game draw (wall empty)"""
        self.phase = GamePhase.ENDED
        
        # Check tenpai players
        tenpai_players = [i for i, p in enumerate(self.players) if p.is_tenpai()]
        
        # Tenpai payments (3000 points distributed)
        if len(tenpai_players) > 0 and len(tenpai_players) < 4:
            payment_per_tenpai = 3000 // len(tenpai_players)
            payment_per_noten = 3000 // (4 - len(tenpai_players))
            
            for i, player in enumerate(self.players):
                if i in tenpai_players:
                    player.add_score(payment_per_tenpai)
                else:
                    player.add_score(-payment_per_noten)
        
        return {
            "success": True,
            "message": "Game drawn - wall empty",
            "game_ended": True,
            "tenpai_players": tenpai_players
        }

    def advance_turn(self):
        """Advance to next player's turn"""
        if self.last_discard is None:  # No calls were made
            self.current_player = (self.current_player + 1) % 4
            
            # Draw tile for new current player
            if self.wall.tiles_remaining() > 0:
                tile = self.wall.draw_tile()
                self.players[self.current_player].draw_tile(tile)
            
            self.turn_number += 1

    def start_new_round(self):
        """Start a new round/hand"""
        # Reset hands
        for player in self.players:
            player.hand = Hand()
        
        # Create new wall
        self.wall = Wall(self.wall.use_red_fives)
        
        # Reset game state
        self.current_player = self.dealer
        self.turn_number = 0
        self.last_discard = None
        self.last_discard_player = None
        self.phase = GamePhase.DEALING
        
        # Deal new hands
        self._deal_initial_hands()

    def advance_round(self):
        """Advance to next round (change dealer)"""
        # Update dealer
        self.dealer = (self.dealer + 1) % 4
        
        # Update seat winds
        for i, player in enumerate(self.players):
            winds = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
            player.seat_wind = winds[(i - self.dealer) % 4]
            player.is_dealer = (i == self.dealer)
        
        # Check if we need to advance round wind
        if self.dealer == 0:  # Full rotation
            if self.round_wind == Wind.EAST:
                self.round_wind = Wind.SOUTH
            elif self.round_wind == Wind.SOUTH:
                # Game ends after South round (can be extended)
                return True
        
        self.round_number += 1
        return False

    def is_game_over(self) -> bool:
        """Check if game should end"""
        # Check if any player is below 0 points
        if any(player.score < 0 for player in self.players):
            return True
        
        # Check if we've completed South round
        if self.round_wind == Wind.SOUTH and self.dealer == 0:
            return True
        
        return False

    def get_final_rankings(self) -> List[Dict[str, Any]]:
        """Get final player rankings"""
        players_with_scores = [
            {
                "name": player.name,
                "score": player.score,
                "rank": 0
            }
            for player in self.players
        ]
        
        # Sort by score (highest first)
        players_with_scores.sort(key=lambda x: x["score"], reverse=True)
        
        # Assign ranks
        for i, player_data in enumerate(players_with_scores):
            player_data["rank"] = i + 1
        
        return players_with_scores

    def get_safe_tiles_for_player(self, player_index: int) -> List[str]:
        """Get tiles that are safe to discard for a player"""
        player = self.players[player_index]
        safe_tiles = set()
        
        # Tiles already discarded by all players are generally safe
        for p in self.players:
            safe_tiles.update(p.hand.discards)
        
        # Remove tiles that could be winning tiles for tenpai players
        for i, p in enumerate(self.players):
            if i != player_index and p.is_tenpai():
                winning_tiles = p.hand.get_winning_tiles()
                safe_tiles -= winning_tiles
        
        return [str(tile) for tile in safe_tiles if tile in player.hand.concealed_tiles]

    def get_dangerous_tiles_for_player(self, player_index: int) -> List[str]:
        """Get tiles that are dangerous to discard"""
        dangerous_tiles = set()
        
        # Check what tiles other tenpai players are waiting for
        for i, player in enumerate(self.players):
            if i != player_index and player.is_tenpai():
                dangerous_tiles.update(player.hand.get_winning_tiles())
        
        current_player = self.players[player_index]
        return [str(tile) for tile in dangerous_tiles if tile in current_player.hand.concealed_tiles]

    def can_call_closed_kan(self, player_index: int) -> List[str]:
        """Get tiles that can be used for closed kan"""
        player = self.players[player_index]
        kan_tiles = []
        
        # Count tiles in hand
        tile_counts = {}
        for tile in player.hand.concealed_tiles:
            tile_counts[tile] = tile_counts.get(tile, 0) + 1
        
        # Find tiles with 4 copies
        for tile, count in tile_counts.items():
            if count == 4:
                kan_tiles.append(str(tile))
        
        return kan_tiles

    def can_upgrade_pon_to_kan(self, player_index: int) -> List[str]:
        """Get pon melds that can be upgraded to kan"""
        player = self.players[player_index]
        upgradeable = []
        
        for meld in player.hand.melds:
            if meld.is_triplet() and meld.is_open:
                meld_tile = meld.tiles[0]
                # Check if we have the 4th tile in hand
                if meld_tile in player.hand.concealed_tiles:
                    upgradeable.append(str(meld_tile))
        
        return upgradeable

    def execute_closed_kan(self, player_index: int, tile_str: str) -> Dict[str, Any]:
        """Execute closed kan declaration"""
        if player_index != self.current_player:
            return {"success": False, "message": "Not your turn"}
        
        player = self.players[player_index]
        
        # Find the tile
        target_tile = None
        for tile in player.hand.concealed_tiles:
            if str(tile) == tile_str:
                target_tile = tile
                break
        
        if not target_tile:
            return {"success": False, "message": "Tile not found"}
        
        # Check if we have 4 of this tile
        if player.hand.concealed_tiles.count(target_tile) < 4:
            return {"success": False, "message": "Need 4 tiles for kan"}
        
        # Execute closed kan
        player.call_kan(target_tile)
        
        # Add dora indicator
        self.wall.add_dora_indicator()
        
        # Draw replacement tile
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
        
        return {"success": True, "message": f"Declared closed kan of {target_tile}"}

    def get_game_log(self) -> List[Dict[str, Any]]:
        """Get game action log (simplified)"""
        # This would typically store all actions throughout the game
        # For now, return current state summary
        return [
            {
                "turn": self.turn_number,
                "action": "game_state",
                "data": self.get_game_state()
            }
        ]

    def reset_game(self):
        """Reset game to initial state"""
        # Reset player scores
        for player in self.players:
            player.score = 25000
            player.hand = Hand()
            player.riichi_bets = 0
        
        # Reset game state
        self.dealer = 0
        self.current_player = 0
        self.round_wind = Wind.EAST
        self.round_number = 1
        self.turn_number = 0
        self.riichi_bets = 0
        self.honba = 0
        self.last_discard = None
        self.last_discard_player = None
        
        # Set dealer
        self.players[0].is_dealer = True
        for i in range(1, 4):
            self.players[i].is_dealer = False
        
        # Create new wall and deal
        self.wall = Wall(self.wall.use_red_fives)
        self._deal_initial_hands()
