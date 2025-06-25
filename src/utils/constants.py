"""
Constants and utility functions for Riichi Mahjong
"""

from typing import Dict, List
from tiles.tile import Tile, Suit, Wind, Dragon

# Scoring constants
STARTING_POINTS = 25000
RIICHI_COST = 1000
TENPAI_PAYMENT = 3000

# Game flow constants
INITIAL_HAND_SIZE = 13
WINNING_HAND_SIZE = 14
DEAD_WALL_SIZE = 14

# Yaku han values
YAKU_HAN_VALUES = {
    'riichi': 1,
    'menzen_tsumo': 1,
    'tanyao': 1,
    'pinfu': 1,
    'yakuhai': 1,
    'iipeikou': 1,
    'toitoi': 2,
    'sanankou': 2,
    'honitsu_open': 2,
    'honitsu_closed': 3,
    'chinitsu_open': 5,
    'chinitsu_closed': 6,
}

# Tile Unicode representations (for display)
TILE_UNICODE = {
    # Souzu (Bamboo)
    '1sou': '🀐', '2sou': '🀑', '3sou': '🀒', '4sou': '🀓', '5sou': '🀔',
    '6sou': '🀕', '7sou': '🀖', '8sou': '🀗', '9sou': '🀘',
    # Pinzu (Circles)
    '1pin': '🀙', '2pin': '🀚', '3pin': '🀛', '4pin': '🀜', '5pin': '🀝',
    '6pin': '🀞', '7pin': '🀟', '8pin': '🀠', '9pin': '🀡',
    # Manzu (Characters)
    '1man': '🀇', '2man': '🀈', '3man': '🀉', '4man': '🀊', '5man': '🀋',
    '6man': '🀌', '7man': '🀍', '8man': '🀎', '9man': '🀏',
    # Winds
    'east': '🀀', 'south': '🀁', 'west': '🀂', 'north': '🀃',
    # Dragons
    'white': '🀆', 'green': '🀅', 'red': '🀄',
}

def get_tile_unicode(tile: Tile) -> str:
    """Get Unicode representation of a tile"""
    tile_str = str(tile)
    return TILE_UNICODE.get(tile_str, tile_str)

def format_hand_display(tiles: List[Tile]) -> str:
    """Format hand for display"""
    return ' '.join(get_tile_unicode(tile) for tile in tiles)
