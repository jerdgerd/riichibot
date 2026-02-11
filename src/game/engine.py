import random
from enum import Enum
from typing import Any, Dict, List, Optional

from game.hand import Hand, Meld
from game.player import Player
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
        self.last_action_was_kan_draw = False
        self.has_open_call = False
        self.pending_chankan_tile: Optional[Tile] = None
        self.pending_chankan_from: Optional[int] = None
        self.pending_chankan_responders: set[int] = set()

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
                    "is_tenpai": p.is_tenpai(),
                }
                for p in self.players
            ],
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
                    "is_open": meld.is_open,
                }
                for meld in player.hand.melds
            ],
            "winning_tiles": [str(tile) for tile in player.hand.get_winning_tiles()],
            "is_tenpai": player.is_tenpai(),
            "can_riichi": self._can_declare_riichi(player_index),
            "closed_kan_tiles": self.can_call_closed_kan(player_index),
            "upgrade_kan_tiles": self.can_upgrade_pon_to_kan(player_index),
        }

    def get_valid_actions(self, player_index: int) -> List[str]:
        """Get valid actions for a player"""
        player = self.players[player_index]
        actions = []

        if self.pending_chankan_tile and player_index == self.pending_chankan_from:
            return actions

        if self.current_player == player_index:
            # Current player's turn
            meld_tile_count = sum(len(meld.tiles) for meld in player.hand.melds)
            total_tiles = len(player.hand.concealed_tiles) + meld_tile_count

            if total_tiles == 14:
                actions.append("discard")
                winning_tile = (
                    player.hand.last_drawn_tile
                    if player.hand.last_drawn_tile is not None
                    else player.hand.concealed_tiles[-1]
                )
                if player.can_tsumo() and self._has_yaku_for_win(
                    player, winning_tile, is_tsumo=True
                ):
                    actions.append("tsumo")
                if self.can_call_closed_kan(player_index) or self.can_upgrade_pon_to_kan(
                    player_index
                ):
                    actions.append("kan")
                if self._can_declare_riichi(player_index):
                    actions.append("riichi")
            elif total_tiles == 13:
                # Player needs to draw first - this shouldn't happen in normal flow
                # Force a tile draw if wall has tiles
                if self.wall.tiles_remaining() > 0:
                    tile = self.wall.draw_tile()
                    player.draw_tile(tile)
                    # Now they should be able to discard
                    actions.append("discard")
                    winning_tile = (
                        player.hand.last_drawn_tile
                        if player.hand.last_drawn_tile is not None
                        else player.hand.concealed_tiles[-1]
                    )
                    if player.can_tsumo() and self._has_yaku_for_win(
                        player, winning_tile, is_tsumo=True
                    ):
                        actions.append("tsumo")
                    if self._can_declare_riichi(player_index):
                        actions.append("riichi")
                else:
                    # Wall empty, handle draw
                    pass
        else:
            if (
                self.pending_chankan_tile
                and player_index in self.pending_chankan_responders
            ):
                if player.can_call_ron(self.pending_chankan_tile) and self._has_yaku_for_win(
                    player,
                    self.pending_chankan_tile,
                    is_tsumo=False,
                    is_chankan=True,
                ):
                    actions.append("ron")
                actions.append("pass")
                return actions

            # Other players can call discards
            if self.last_discard:
                if player.can_call_ron(self.last_discard) and self._has_yaku_for_win(
                    player, self.last_discard, is_tsumo=False
                ):
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

    def _has_yaku_for_win(
        self,
        player: Player,
        winning_tile: Tile,
        is_tsumo: bool,
        *,
        is_chankan: bool = False,
    ) -> bool:
        """Check if a win has at least one non-dora yaku"""
        player_index = self.players.index(player)
        yaku_context = self._build_yaku_context(
            player_index, is_tsumo=is_tsumo, is_chankan=is_chankan
        )
        yaku_list = YakuChecker.check_all_yaku(
            player.hand,
            winning_tile,
            is_tsumo,
            player.seat_wind,
            self.round_wind,
            self.wall.get_dora_tiles(),
            self.wall.get_ura_dora_tiles() if player.hand.is_riichi else None,
            **yaku_context,
        )

        return any(yaku.name != "Dora" for yaku in yaku_list)

    def _build_yaku_context(
        self, player_index: int, *, is_tsumo: bool, is_chankan: bool = False
    ) -> Dict[str, bool]:
        """Build situational yaku context flags for the current win check."""
        player = self.players[player_index]
        no_discards_yet = all(len(p.hand.discards) == 0 for p in self.players)
        last_tile = self.wall.tiles_remaining() == 0

        return {
            "is_ippatsu": player.hand.is_riichi and player.hand.ippatsu_eligible,
            "is_double_riichi": player.hand.is_riichi and player.hand.riichi_turn == 0,
            "is_rinshan": is_tsumo and self.last_action_was_kan_draw,
            "is_chankan": is_chankan,
            "is_haitei": is_tsumo and last_tile,
            "is_houtei": (not is_tsumo) and last_tile,
            "is_tenhou": (
                is_tsumo
                and player.is_dealer
                and self.turn_number == 0
                and no_discards_yet
                and not self.has_open_call
            ),
            "is_chiihou": (
                is_tsumo
                and not player.is_dealer
                and len(player.hand.discards) == 0
                and self.turn_number <= 3
                and not self.has_open_call
            ),
        }

    def _clear_ippatsu_all(self):
        for player in self.players:
            player.hand.ippatsu_eligible = False

    def _clear_pending_chankan(self):
        self.pending_chankan_tile = None
        self.pending_chankan_from = None
        self.pending_chankan_responders = set()

    def _find_chankan_responders(self, tile: Tile, kan_player: int) -> List[int]:
        responders: List[int] = []
        for idx, player in enumerate(self.players):
            if idx == kan_player:
                continue
            if not player.can_call_ron(tile):
                continue
            if not self._has_yaku_for_win(
                player, tile, is_tsumo=False, is_chankan=True
            ):
                continue
            responders.append(idx)
        return responders

    def execute_action(
        self, player_index: int, action: str, **kwargs
    ) -> Dict[str, Any]:
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
                tile_str = kwargs.get("tile")
                if self.last_discard:
                    result = self._execute_kan(player_index)
                else:
                    result = self._execute_closed_or_added_kan(player_index, tile_str)

            elif action == "pass":
                result = self._execute_pass(player_index)

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
        self.last_action_was_kan_draw = False

        # Check furiten for all players
        for p in self.players:
            p.hand.check_furiten()

        return {"success": True, "message": f"Discarded {discarded_tile}"}

    def _execute_tsumo(self, player_index: int) -> Dict[str, Any]:
        """Execute tsumo (self-draw win)"""
        player = self.players[player_index]

        if not player.can_tsumo():
            return {"success": False, "message": "Cannot tsumo"}

        # Calculate score
        winning_tile = (
            player.hand.last_drawn_tile
            if player.hand.last_drawn_tile is not None
            else player.hand.concealed_tiles[-1]
        )
        yaku_context = self._build_yaku_context(player_index, is_tsumo=True)
        yaku_list = YakuChecker.check_all_yaku(
            player.hand,
            winning_tile,
            True,
            player.seat_wind,
            self.round_wind,
            self.wall.get_dora_tiles(),
            self.wall.get_ura_dora_tiles() if player.hand.is_riichi else None,
            **yaku_context,
        )

        if not any(yaku.name != "Dora" for yaku in yaku_list):
            return {"success": False, "message": "No yaku - cannot win"}

        score, payments = Scoring.calculate_score(
            yaku_list,
            player.is_dealer,
            True,
            hand=player.hand,
            winning_tile=winning_tile,
            seat_wind=player.seat_wind,
            round_wind=self.round_wind,
            honba=self.honba,
        )

        # Apply payments
        self._apply_tsumo_payments(player_index, score, payments)

        self._clear_pending_chankan()
        self.phase = GamePhase.ENDED
        self._update_honba_after_win(winner_index=player_index)

        return {
            "success": True,
            "message": f"{player.name} won by tsumo!",
            "game_ended": True,
            "winner": player_index,
            "score": score,
            "yaku": [{"name": y.name, "han": y.han} for y in yaku_list],
        }

    def _execute_ron(self, player_index: int) -> Dict[str, Any]:
        """Execute ron (win on discard)"""
        player = self.players[player_index]
        is_chankan = False
        winning_tile: Optional[Tile] = None
        discarder_index: Optional[int] = None

        if (
            self.pending_chankan_tile
            and player_index in self.pending_chankan_responders
        ):
            is_chankan = True
            winning_tile = self.pending_chankan_tile
            discarder_index = self.pending_chankan_from
        elif self.last_discard:
            winning_tile = self.last_discard
            discarder_index = self.last_discard_player

        if (
            winning_tile is None
            or discarder_index is None
            or not player.can_call_ron(winning_tile)
        ):
            return {"success": False, "message": "Cannot call ron"}

        # Calculate score
        yaku_context = self._build_yaku_context(
            player_index, is_tsumo=False, is_chankan=is_chankan
        )
        yaku_list = YakuChecker.check_all_yaku(
            player.hand,
            winning_tile,
            False,
            player.seat_wind,
            self.round_wind,
            self.wall.get_dora_tiles(),
            self.wall.get_ura_dora_tiles() if player.hand.is_riichi else None,
            **yaku_context,
        )

        if not any(yaku.name != "Dora" for yaku in yaku_list):
            return {"success": False, "message": "No yaku - cannot win"}

        score, payments = Scoring.calculate_score(
            yaku_list,
            player.is_dealer,
            False,
            hand=player.hand,
            winning_tile=winning_tile,
            seat_wind=player.seat_wind,
            round_wind=self.round_wind,
            honba=self.honba,
        )

        # Apply payments
        discarder = self.players[discarder_index]
        discarder.add_score(-score)
        player.add_score(score)

        # Add riichi bets
        player.add_score(self.riichi_bets * 1000)
        self.riichi_bets = 0

        self._clear_pending_chankan()
        self.phase = GamePhase.ENDED
        self._update_honba_after_win(winner_index=player_index)

        return {
            "success": True,
            "message": f"{player.name} won by ron!",
            "game_ended": True,
            "winner": player_index,
            "score": score,
            "yaku": [{"name": y.name, "han": y.han} for y in yaku_list],
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

        discarded_tile = player.discard_tile(
            tile_to_discard, from_riichi_declaration=True
        )
        self.last_discard = discarded_tile
        self.last_discard_player = player_index
        self.last_action_was_kan_draw = False

        return {
            "success": True,
            "message": f"{player.name} declared riichi and discarded {discarded_tile}",
        }

    def _execute_pass(self, player_index: int) -> Dict[str, Any]:
        player = self.players[player_index]

        if self.pending_chankan_tile and player_index in self.pending_chankan_responders:
            if player.can_call_ron(self.pending_chankan_tile):
                player.hand.temp_furiten = True

            self.pending_chankan_responders.discard(player_index)
            if self.pending_chankan_responders:
                return {"success": True, "message": "Passed chankan"}

            kan_player = self.pending_chankan_from
            kan_tile = self.pending_chankan_tile
            self._clear_pending_chankan()
            if kan_player is None or kan_tile is None:
                return {"success": False, "message": "Invalid chankan state"}

            return self._perform_added_kan(kan_player, kan_tile)

        if self.last_discard and player_index != self.current_player:
            if player.can_call_ron(self.last_discard):
                player.hand.temp_furiten = True

        return {"success": True, "message": "Passed"}

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
        self._clear_ippatsu_all()
        self.has_open_call = True
        self.current_player = player_index
        self.last_discard = None
        self.last_action_was_kan_draw = False

        return {"success": True, "message": f"{player.name} called chii"}

    def _execute_pon(self, player_index: int) -> Dict[str, Any]:
        """Execute pon call"""
        player = self.players[player_index]

        if not self.last_discard or not player.can_call_pon(self.last_discard):
            return {"success": False, "message": "Cannot call pon"}

        player.call_pon(self.last_discard, self.last_discard_player)
        self._clear_ippatsu_all()
        self.has_open_call = True
        self.current_player = player_index
        self.last_discard = None
        self.last_action_was_kan_draw = False

        return {"success": True, "message": f"{player.name} called pon"}

    def _execute_kan(self, player_index: int) -> Dict[str, Any]:
        """Execute kan call"""
        player = self.players[player_index]

        if self.last_discard:
            # Open kan from discard
            if not player.can_call_kan(self.last_discard):
                return {"success": False, "message": "Cannot call kan"}

            player.call_kan(self.last_discard, self.last_discard_player)
            self._clear_ippatsu_all()
            self.has_open_call = True
            self.current_player = player_index
            self.last_discard = None
        else:
            # Closed kan from hand
            # This would need additional logic to specify which tile to kan
            return {"success": False, "message": "Closed kan not implemented"}

        # Add new dora indicator
        self.wall.add_dora_indicator()

        # Player draws replacement tile
        self.last_action_was_kan_draw = False
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
            self.last_action_was_kan_draw = True

        return {"success": True, "message": f"{player.name} called kan"}

    def _execute_closed_or_added_kan(
        self, player_index: int, tile_str: Optional[str]
    ) -> Dict[str, Any]:
        """Execute closed or added kan on the current player's turn"""
        if player_index != self.current_player:
            return {"success": False, "message": "Not your turn"}

        if not tile_str:
            return {"success": False, "message": "Tile required for kan"}

        player = self.players[player_index]

        target_tile = None
        for tile in player.hand.concealed_tiles:
            if str(tile) == tile_str:
                target_tile = tile
                break

        if not target_tile:
            return {"success": False, "message": "Tile not found in hand"}

        if player.can_upgrade_pon_to_kan(target_tile):
            if not self._riichi_kan_allowed(player, target_tile):
                return {"success": False, "message": "Riichi kan restriction"}
            self._clear_ippatsu_all()
            responders = self._find_chankan_responders(target_tile, player_index)
            if responders:
                self.pending_chankan_tile = target_tile
                self.pending_chankan_from = player_index
                self.pending_chankan_responders = set(responders)
                return {
                    "success": True,
                    "message": "Added kan pending chankan responses",
                    "pending_chankan": True,
                    "responders": responders,
                }

            return self._perform_added_kan(player_index, target_tile)
        elif player.hand.concealed_tiles.count(target_tile) >= 4:
            if not self._riichi_kan_allowed(player, target_tile):
                return {"success": False, "message": "Riichi kan restriction"}
            player.call_kan(target_tile)
        else:
            return {"success": False, "message": "Cannot declare kan"}

        self._clear_ippatsu_all()

        # Add new dora indicator
        self.wall.add_dora_indicator()

        # Player draws replacement tile
        self.last_action_was_kan_draw = False
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
            self.last_action_was_kan_draw = True

        return {"success": True, "message": f"{player.name} declared kan"}

    def _perform_added_kan(self, player_index: int, target_tile: Tile) -> Dict[str, Any]:
        player = self.players[player_index]
        player.upgrade_pon_to_kan(target_tile)
        self.has_open_call = True

        # Add new dora indicator
        self.wall.add_dora_indicator()

        # Player draws replacement tile
        self.last_action_was_kan_draw = False
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
            self.last_action_was_kan_draw = True

        return {"success": True, "message": f"{player.name} declared kan"}

    def _can_declare_riichi(self, player_index: int) -> bool:
        """Check if player can declare riichi"""
        player = self.players[player_index]
        return (
            player.hand.is_closed()
            and player.is_tenpai()
            and player.score >= 1000
            and not player.hand.is_riichi
        )

    def _apply_tsumo_payments(
        self, winner_index: int, score: int, payments: Dict[str, int]
    ):
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
        self.honba += 1
        self._clear_pending_chankan()

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
            "tenpai_players": tenpai_players,
        }

    def _update_honba_after_win(self, winner_index: int):
        winner = self.players[winner_index]
        if winner.is_dealer:
            self.honba += 1
        else:
            self.honba = 0

    def advance_turn(self):
        """Advance to next player's turn"""
        if self.last_discard is None:  # No calls were made
            self.current_player = (self.current_player + 1) % 4
            self.last_action_was_kan_draw = False

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
        self.last_action_was_kan_draw = False
        self.has_open_call = False
        self._clear_pending_chankan()

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
            player.is_dealer = i == self.dealer

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
            {"name": player.name, "score": player.score, "rank": 0}
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
        return [
            str(tile)
            for tile in dangerous_tiles
            if tile in current_player.hand.concealed_tiles
        ]

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
                if self._riichi_kan_allowed(player, tile):
                    kan_tiles.append(str(tile))

        return kan_tiles

    def can_upgrade_pon_to_kan(self, player_index: int) -> List[str]:
        """Get pon melds that can be upgraded to kan"""
        player = self.players[player_index]
        if player.hand.is_riichi:
            return []
        upgradeable = []

        for meld in player.hand.melds:
            if meld.is_triplet() and meld.is_open:
                meld_tile = meld.tiles[0]
                # Check if we have the 4th tile in hand
                if meld_tile in player.hand.concealed_tiles:
                    upgradeable.append(str(meld_tile))

        return upgradeable

    def _riichi_kan_allowed(self, player: Player, kan_tile: Tile) -> bool:
        """Check riichi kan restrictions (wait must not change)."""
        if not player.hand.is_riichi:
            return True

        if player.hand.concealed_tiles.count(kan_tile) < 4:
            return False

        before_waits = player.hand.get_winning_tiles_with_fixed_melds(
            player.hand.concealed_tiles, fixed_melds=len(player.hand.melds)
        )

        after_tiles = player.hand.concealed_tiles[:]
        for _ in range(4):
            after_tiles.remove(kan_tile)

        after_waits = player.hand.get_winning_tiles_with_fixed_melds(
            after_tiles, fixed_melds=len(player.hand.melds) + 1
        )

        return before_waits == after_waits

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
        self._clear_ippatsu_all()

        # Add dora indicator
        self.wall.add_dora_indicator()

        # Draw replacement tile
        self.last_action_was_kan_draw = False
        if self.wall.tiles_remaining() > 0:
            replacement_tile = self.wall.draw_tile()
            player.draw_tile(replacement_tile)
            self.last_action_was_kan_draw = True

        return {"success": True, "message": f"Declared closed kan of {target_tile}"}

    def get_game_log(self) -> List[Dict[str, Any]]:
        """Get game action log (simplified)"""
        # This would typically store all actions throughout the game
        # For now, return current state summary
        return [
            {
                "turn": self.turn_number,
                "action": "game_state",
                "data": self.get_game_state(),
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
        self.last_action_was_kan_draw = False
        self.has_open_call = False
        self._clear_pending_chankan()

        # Set dealer
        self.players[0].is_dealer = True
        for i in range(1, 4):
            self.players[i].is_dealer = False

        # Create new wall and deal
        self.wall = Wall(self.wall.use_red_fives)
        self._deal_initial_hands()
