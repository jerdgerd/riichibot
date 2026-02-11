from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from tiles.tile import Suit, Tile


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
        self.ippatsu_eligible: bool = False
        self.last_drawn_tile: Optional[Tile] = None
        self.furiten_state: bool = False
        self.temp_furiten: bool = False

    def add_tile(self, tile: Tile):
        """Add tile to concealed hand"""
        self.concealed_tiles.append(tile)
        self.last_drawn_tile = tile
        # Temporary furiten clears on the player's next draw.
        self.temp_furiten = False
        self.concealed_tiles.sort(key=lambda t: (t.suit.value, t.value or 0))

    def remove_tile(self, tile: Tile) -> bool:
        """Remove tile from concealed hand"""
        if tile in self.concealed_tiles:
            self.concealed_tiles.remove(tile)
            return True
        return False

    def discard_tile(self, tile: Tile, *, from_riichi_declaration: bool = False):
        """Discard a tile"""
        if self.remove_tile(tile):
            self.discards.append(tile)
            self.last_drawn_tile = None
            # Ippatsu only survives until the player's first post-riichi discard.
            if self.is_riichi and self.ippatsu_eligible and not from_riichi_declaration:
                self.ippatsu_eligible = False
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

    def get_winning_tiles_with_fixed_melds(
        self, concealed_tiles: List[Tile], fixed_melds: int
    ) -> Set[Tile]:
        """Get winning tiles for a hand with fixed melds (e.g., after kan)."""
        winning_tiles = set()
        all_possible_tiles = self._get_all_possible_tiles()

        for tile in all_possible_tiles:
            test_tiles = concealed_tiles + [tile]
            if self._is_complete_standard_hand(test_tiles, fixed_melds):
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
        from tiles.tile import Dragon, Wind

        for wind in Wind:
            tiles.append(Tile(Suit.WIND, wind=wind))
        for dragon in Dragon:
            tiles.append(Tile(Suit.DRAGON, dragon=dragon))
        return tiles

    def _is_complete_hand(self, tiles: List[Tile]) -> bool:
        """Check if tiles form a complete winning hand"""
        if len(tiles) != 14:
            return False

        if self._is_kokushi(tiles):
            return True

        if self._is_chiitoitsu(tiles):
            return True

        if self._is_complete_standard_hand(tiles, fixed_melds=0):
            return True

        return False

    def _is_complete_standard_hand(self, tiles: List[Tile], fixed_melds: int) -> bool:
        """Check if tiles form a standard hand with fixed melds."""
        melds_needed = 4 - fixed_melds
        if melds_needed < 0:
            return False

        if len(tiles) != 2 + melds_needed * 3:
            return False

        # Try to find a pair and remove it
        for tile in set(tiles):
            if tiles.count(tile) >= 2:
                remaining = tiles[:]
                remaining.remove(tile)
                remaining.remove(tile)

                if self._can_form_melds(remaining, melds_needed):
                    return True

        return False

    def _can_form_melds(self, tiles: List[Tile], melds_needed: int) -> bool:
        """Check if tiles can form the remaining melds (triplets/sequences)."""
        if melds_needed == 0:
            return len(tiles) == 0
        if len(tiles) != melds_needed * 3:
            return False

        tiles_sorted = tiles[:]
        tiles_sorted.sort(key=lambda t: (t.suit.value, t.value or 0))

        # Try to form triplet first
        first_tile = tiles_sorted[0]
        if tiles_sorted.count(first_tile) >= 3:
            # Remove triplet
            triplet_remaining = tiles_sorted[:]
            for _ in range(3):
                triplet_remaining.remove(first_tile)
            if self._can_form_melds(triplet_remaining, melds_needed - 1):
                return True

        # Try to form sequence (only for number tiles)
        if (
            first_tile.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]
            and first_tile.value <= 7
        ):
            tile2 = Tile(first_tile.suit, first_tile.value + 1)
            tile3 = Tile(first_tile.suit, first_tile.value + 2)

            if tile2 in tiles_sorted and tile3 in tiles_sorted:
                # Remove sequence
                sequence_remaining = tiles_sorted[:]
                sequence_remaining.remove(first_tile)
                sequence_remaining.remove(tile2)
                sequence_remaining.remove(tile3)
                if self._can_form_melds(sequence_remaining, melds_needed - 1):
                    return True

        return False

    def _is_chiitoitsu(self, tiles: List[Tile]) -> bool:
        """Check for seven pairs."""
        if len(tiles) != 14:
            return False

        pair_counts = [tiles.count(tile) for tile in set(tiles)]
        return len(pair_counts) == 7 and all(count == 2 for count in pair_counts)

    def _is_kokushi(self, tiles: List[Tile]) -> bool:
        """Check for thirteen orphans."""
        if len(tiles) != 14:
            return False

        terminals_and_honors = []
        for suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            terminals_and_honors.append(Tile(suit, 1))
            terminals_and_honors.append(Tile(suit, 9))

        from tiles.tile import Dragon, Wind

        for wind in Wind:
            terminals_and_honors.append(Tile(Suit.WIND, wind=wind))
        for dragon in Dragon:
            terminals_and_honors.append(Tile(Suit.DRAGON, dragon=dragon))

        unique_needed = set(terminals_and_honors)
        tile_set = set(tiles)

        if not unique_needed.issubset(tile_set):
            return False

        # Must have one duplicate among terminals/honors
        for tile in unique_needed:
            if tiles.count(tile) >= 2:
                return True

        return False


    def check_furiten(self, all_discards: Optional[List[List[Tile]]] = None) -> bool:
        """Check permanent furiten state (own discard furiten)."""
        winning_tiles = self.get_winning_tiles()

        # Check own discards
        for tile in self.discards:
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
        self.ippatsu_eligible = True

    def get_all_tiles(self) -> List[Tile]:
        """Get all tiles in hand (concealed + melds)"""
        all_tiles = self.concealed_tiles[:]
        for meld in self.melds:
            all_tiles.extend(meld.tiles)
        return all_tiles
