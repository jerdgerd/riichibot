from enum import Enum
from dataclasses import dataclass
from typing import Optional

class Suit(Enum):
    SOUZU = "sou"  # Bamboo
    PINZU = "pin"  # Circles
    MANZU = "man"  # Characters
    WIND = "wind"
    DRAGON = "dragon"

class Wind(Enum):
    EAST = "east"
    SOUTH = "south"
    WEST = "west"
    NORTH = "north"

class Dragon(Enum):
    GREEN = "green"
    RED = "red"
    WHITE = "white"

@dataclass(frozen=True)
class Tile:
    suit: Suit
    value: Optional[int] = None
    wind: Optional[Wind] = None
    dragon: Optional[Dragon] = None
    is_red: bool = False
    
    def __post_init__(self):
        if self.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            if not (1 <= self.value <= 9):
                raise ValueError("Number tiles must have value 1-9")
        elif self.suit == Suit.WIND:
            if not self.wind:
                raise ValueError("Wind tiles must specify wind")
        elif self.suit == Suit.DRAGON:
            if not self.dragon:
                raise ValueError("Dragon tiles must specify dragon")
    
    def is_terminal(self) -> bool:
        """Check if tile is 1 or 9"""
        return self.value in [1, 9] if self.value else False
    
    def is_honor(self) -> bool:
        """Check if tile is wind or dragon"""
        return self.suit in [Suit.WIND, Suit.DRAGON]
    
    def is_terminal_or_honor(self) -> bool:
        """Check if tile is terminal (1/9) or honor"""
        return self.is_terminal() or self.is_honor()
    
    def next_tile(self) -> 'Tile':
        """Get next tile for dora calculation"""
        if self.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            next_val = 1 if self.value == 9 else self.value + 1
            return Tile(self.suit, next_val)
        elif self.suit == Suit.WIND:
            wind_cycle = [Wind.EAST, Wind.SOUTH, Wind.WEST, Wind.NORTH]
            current_idx = wind_cycle.index(self.wind)
            next_wind = wind_cycle[(current_idx + 1) % 4]
            return Tile(Suit.WIND, wind=next_wind)
        elif self.suit == Suit.DRAGON:
            dragon_cycle = [Dragon.GREEN, Dragon.RED, Dragon.WHITE]
            current_idx = dragon_cycle.index(self.dragon)
            next_dragon = dragon_cycle[(current_idx + 1) % 3]
            return Tile(Suit.DRAGON, dragon=next_dragon)
    
    def __str__(self):
        if self.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            color = "r" if self.is_red else ""
            return f"{self.value}{color}{self.suit.value}"
        elif self.suit == Suit.WIND:
            return self.wind.value
        elif self.suit == Suit.DRAGON:
            return self.dragon.value
