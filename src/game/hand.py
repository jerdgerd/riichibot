from typing import List, Set, Optional, Tuple
from dataclasses import dataclass
from tiles.tile import Tile, Suit


@dataclass
class Meld:
    tiles: List[Tile]
    is_open: bool = False
    called_from: Optional[int] = None  # Player position who discarded

    @property
    def meld_type(self) -> str:
        if len(self.tiles) == 2:
            return "pair"
        elif len(self.tiles) == 3:
            if all(t == self.tiles[0] for t in self.tiles):
                return "triplet"
            else:
                return "sequence"
        elif len(self.tiles) == 4:
            return "kan"
        return "unknown"

    def is_sequence(self) -> bool:
        return self.meld_type == "sequence"

    def is_triplet(self) -> bool:
        return self.meld_type == "triplet"

    def is_kan(self) -> bool:
        return self.meld_type == "kan"


class Hand:
    def __init__(self):
        self.concealed_tiles: List[Tile] = []
        self.melds: List[Meld] = []
        self.discards: List[Tile] = []
        self.is_riichi: bool = False
        self.riichi_turn: Optional[int] = None
        self.furiten_state: bool = False
        self.temp_furiten: bool = False

    def add_tile(self, tile: Tile):
        """Add tile to concealed hand"""
        self.concealed_tiles.append(tile)
        self.concealed_tiles.sort(key=lambda t: (t.suit.value, t.value or 0))

    def remove_tile(self, tile: Tile) -> bool:
        """Remove tile from concealed hand"""
        if tile in self.concealed_tiles:
            self.concealed_tiles.remove(tile)
            return True
        return False

    def discard_tile(self, tile: Tile):
        """Discard a tile"""
        if self.remove_tile(tile):
            self.discards.append(tile)
            self.temp_furiten = False  # Reset temp furiten

    def add_meld(self, meld: Meld):
        """Add completed meld"""
        self.melds.append(meld)

    def is_closed(self) -> bool:
        """Check if hand is closed (no open melds)"""
        return all(not meld.is_open for meld in self.melds)

    def is_tenpai(self) -> bool:
        """Check if hand is one tile away from winning"""
        return len(self.get_winning_tiles()) > 0

    def get_winning_tiles(self) -> Set[Tile]:
        """Get all tiles that would complete the hand"""
        winning_tiles = set()

        # Try each possible tile
        all_possible_tiles = self._get_all_possible_tiles()
        for tile in all_possible_tiles:
            test_hand = self.concealed_tiles + [tile]
            if self._is_complete_hand(test_hand):
                winning_tiles.add(tile)

        return winning_tiles

    def _get_all_possible_tiles(self) -> List[Tile]:
        """Get all possible tiles in the game"""
        tiles = []
        # Number tiles
        for suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            for value in range(1, 10):
                tiles.append(Tile(suit, value))
        # Honor tiles
        from tiles.tile import Wind, Dragon

        for wind in Wind:
            tiles.append(Tile(Suit.WIND, wind=wind))
        for dragon in Dragon:
            tiles.append(Tile(Suit.DRAGON, dragon=dragon))
        return tiles

    def _is_complete_hand(self, tiles: List[Tile]) -> bool:
        """Check if tiles form a complete winning hand"""
        if len(tiles) != 14:
            return False

        # Try to find a pair and remove it
        for i, tile in enumerate(tiles):
            remaining = tiles[:]
            if remaining.count(tile) >= 2:
                # Remove pair
                remaining.remove(tile)
                remaining.remove(tile)

                # Check if remaining 12 tiles can form 4 melds
                if self._can_form_melds(remaining):
                    return True

        return False

    def _can_form_melds(self, tiles: List[Tile]) -> bool:
        """Check if tiles can form exactly 4 melds (triplets/sequences)"""
        if len(tiles) == 0:
            return True
        if len(tiles) % 3 != 0:
            return False

        tiles_copy = tiles[:]
        tiles_copy.sort(key=lambda t: (t.suit.value, t.value or 0))

        # Try to form triplet first
        first_tile = tiles_copy[0]
        if tiles_copy.count(first_tile) >= 3:
            # Remove triplet
            for _ in range(3):
                tiles_copy.remove(first_tile)
            return self._can_form_melds(tiles_copy)

        # Try to form sequence (only for number tiles)
        if (
            first_tile.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]
            and first_tile.value <= 7
        ):
            tile2 = Tile(first_tile.suit, first_tile.value + 1)
            tile3 = Tile(first_tile.suit, first_tile.value + 2)

            if tile2 in tiles_copy and tile3 in tiles_copy:
                # Remove sequence
                tiles_copy.remove(first_tile)
                tiles_copy.remove(tile2)
                tiles_copy.remove(tile3)
                return self._can_form_melds(tiles_copy)

        return False

    def check_furiten(self, all_discards: List[List[Tile]]) -> bool:
        """Check if player is in furiten state"""
        winning_tiles = self.get_winning_tiles()

        # Check own discards
        for tile in self.discards:
            if tile in winning_tiles:
                self.furiten_state = True
                return True

        # Check called tiles in other players' melds
        for player_discards in all_discards:
            for tile in player_discards:
                if tile in winning_tiles:
                    self.furiten_state = True
                    return True

        self.furiten_state = False
        return False

    def declare_riichi(self, turn: int):
        """Declare riichi"""
        if not self.is_closed() or not self.is_tenpai():
            raise ValueError("Cannot declare riichi: hand must be closed and tenpai")

        self.is_riichi = True
        self.riichi_turn = turn

    def get_all_tiles(self) -> List[Tile]:
        """Get all tiles in hand (concealed + melds)"""
        all_tiles = self.concealed_tiles[:]
        for meld in self.melds:
            all_tiles.extend(meld.tiles)
        return all_tiles
