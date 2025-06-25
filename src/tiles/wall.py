import random
from typing import List
from .tile import Tile, Suit, Wind, Dragon

class Wall:
    def __init__(self, use_red_fives: bool = True):
        self.tiles: List[Tile] = []
        self.dead_wall: List[Tile] = []
        self.dora_indicators: List[Tile] = []
        self.use_red_fives = use_red_fives
        self._build_wall()
        self._shuffle()
    
    def _build_wall(self):
        """Build complete set of 136 tiles"""
        # Number tiles (4 of each 1-9 in 3 suits)
        for suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            for value in range(1, 10):
                for _ in range(4):
                    is_red = (self.use_red_fives and value == 5 and 
                             len([t for t in self.tiles if t.suit == suit and t.value == 5]) == 0)
                    self.tiles.append(Tile(suit, value, is_red=is_red))
        
        # Wind tiles (4 of each)
        for wind in Wind:
            for _ in range(4):
                self.tiles.append(Tile(Suit.WIND, wind=wind))
        
        # Dragon tiles (4 of each)
        for dragon in Dragon:
            for _ in range(4):
                self.tiles.append(Tile(Suit.DRAGON, dragon=dragon))
    
    def _shuffle(self):
        """Shuffle tiles and set up dead wall"""
        random.shuffle(self.tiles)
        self.dead_wall = self.tiles[-14:]  # Last 14 tiles
        self.tiles = self.tiles[:-14]
        self.dora_indicators = [self.dead_wall[4]]  # Initial dora indicator
    
    def draw_tile(self) -> Tile:
        """Draw tile from wall"""
        if not self.tiles:
            raise ValueError("Wall is empty")
        return self.tiles.pop(0)
    
    def add_dora_indicator(self):
        """Add new dora indicator when kan is declared"""
        if len(self.dora_indicators) < 4:
            idx = 4 + len(self.dora_indicators)
            self.dora_indicators.append(self.dead_wall[idx])
    
    def get_dora_tiles(self) -> List[Tile]:
        """Get current dora tiles"""
        return [indicator.next_tile() for indicator in self.dora_indicators]
    
    def get_ura_dora_tiles(self) -> List[Tile]:
        """Get ura-dora tiles (under dora indicators)"""
        ura_indicators = []
        for i, _ in enumerate(self.dora_indicators):
            ura_indicators.append(self.dead_wall[9 + i])
        return [indicator.next_tile() for indicator in ura_indicators]
    
    def tiles_remaining(self) -> int:
        return len(self.tiles)
