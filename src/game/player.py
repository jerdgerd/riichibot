from typing import List, Optional

from game.hand import Hand, Meld
from tiles.tile import Tile, Wind


class Player:
    def __init__(self, name: str, seat_wind: Wind):
        self.name = name
        self.seat_wind = seat_wind
        self.hand = Hand()
        self.score = 25000  # Starting score
        self.is_dealer = False
        self.riichi_bets = 0

    def draw_tile(self, tile: Tile):
        """Draw a tile from wall"""
        self.hand.add_tile(tile)

    def discard_tile(self, tile: Tile) -> Tile:
        """Discard a tile"""
        if tile not in self.hand.concealed_tiles:
            raise ValueError("Cannot discard tile not in hand")

        self.hand.discard_tile(tile)
        return tile

    def can_call_chii(self, tile: Tile, from_left: bool) -> List[List[Tile]]:
        """Check if player can call chii (sequence) with discarded tile"""
        if not from_left:  # Chii only from left player
            return []

        if tile.is_honor():  # Cannot make sequences with honor tiles
            return []

        possible_sequences = []

        # Check for sequences where discarded tile completes them
        for offset in [-2, -1, 0]:  # Tile can be 1st, 2nd, or 3rd in sequence
            if tile.value + offset < 1 or tile.value + offset > 7:
                continue

            needed_tiles = []
            for i in range(3):
                if i == -offset:  # This is the discarded tile position
                    continue
                needed_tiles.append(Tile(tile.suit, tile.value + offset + i))

            # Check if we have the needed tiles
            if all(t in self.hand.concealed_tiles for t in needed_tiles):
                sequence = [Tile(tile.suit, tile.value + offset + i) for i in range(3)]
                possible_sequences.append(sequence)

        return possible_sequences

    def can_call_pon(self, tile: Tile) -> bool:
        """Check if player can call pon (triplet) with discarded tile"""
        return self.hand.concealed_tiles.count(tile) >= 2

    def can_call_kan(self, tile: Tile) -> bool:
        """Check if player can call kan with discarded tile"""
        return self.hand.concealed_tiles.count(tile) >= 3

    def can_call_ron(self, tile: Tile) -> bool:
        """Check if player can call ron (win) with discarded tile"""
        if self.hand.furiten_state or self.hand.temp_furiten:
            return False

        return tile in self.hand.get_winning_tiles()

    def can_tsumo(self) -> bool:
        """Check if player can call tsumo (self-draw win)"""
        return len(self.hand.concealed_tiles) == 14 and self.hand.is_tenpai()

    def call_chii(self, tile: Tile, sequence: List[Tile]):
        """Execute chii call"""
        # Remove tiles from hand
        for t in sequence:
            if t != tile:  # Don't remove the called tile
                self.hand.remove_tile(t)

        # Create open meld
        meld = Meld(sequence, is_open=True, called_from=3)  # Left player
        self.hand.add_meld(meld)

    def call_pon(self, tile: Tile, called_from: int):
        """Execute pon call"""
        # Remove two matching tiles from hand
        for _ in range(2):
            self.hand.remove_tile(tile)

        # Create open meld
        triplet = [tile, tile, tile]
        meld = Meld(triplet, is_open=True, called_from=called_from)
        self.hand.add_meld(meld)

    def call_kan(self, tile: Tile, called_from: Optional[int] = None):
        """Execute kan call"""
        if called_from is not None:
            # Open kan from discard
            for _ in range(3):
                self.hand.remove_tile(tile)
            kan = [tile, tile, tile, tile]
            meld = Meld(kan, is_open=True, called_from=called_from)
        else:
            # Closed kan from hand
            for _ in range(4):
                self.hand.remove_tile(tile)
            kan = [tile, tile, tile, tile]
            meld = Meld(kan, is_open=False)

        self.hand.add_meld(meld)

    def declare_riichi(self, turn: int):
        """Declare riichi"""
        if self.score < 1000:
            raise ValueError("Not enough points to declare riichi")

        self.hand.declare_riichi(turn)
        self.score -= 1000
        self.riichi_bets += 1

    def add_score(self, points: int):
        """Add points to player's score"""
        self.score += points

    def is_tenpai(self) -> bool:
        """Check if player is tenpai"""
        return self.hand.is_tenpai()

    def get_safe_tiles(self, other_players: List["Player"]) -> List[Tile]:
        """Get tiles that are safe to discard (already discarded by others)"""
        safe_tiles = []
        for player in other_players:
            safe_tiles.extend(player.hand.discards)
        return list(set(safe_tiles))
