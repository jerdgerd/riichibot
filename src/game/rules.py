from typing import List, Dict, Optional
from dataclasses import dataclass
from ..tiles.tile import Tile, Suit, Wind, Dragon
from .hand import Hand, Meld

@dataclass
class Yaku:
    name: str
    han: int
    closed_only: bool = False
    
class YakuChecker:
    """Check for yaku (winning conditions) in a hand"""
    
    @staticmethod
    def check_all_yaku(hand: Hand, winning_tile: Tile, is_tsumo: bool, 
                       seat_wind: Wind, round_wind: Wind, 
                       dora_tiles: List[Tile], ura_dora_tiles: List[Tile] = None) -> List[Yaku]:
        """Check all possible yaku for a winning hand"""
        yaku_list = []
        all_tiles = hand.get_all_tiles()
        
        # Basic yaku checks
        if YakuChecker._check_riichi(hand):
            yaku_list.append(Yaku("Riichi", 1, closed_only=True))
        
        if YakuChecker._check_menzen_tsumo(hand, is_tsumo):
            yaku_list.append(Yaku("Menzen Tsumo", 1, closed_only=True))
        
        if YakuChecker._check_tanyao(all_tiles):
            yaku_list.append(Yaku("Tanyao", 1))
        
        if YakuChecker._check_pinfu(hand, winning_tile, seat_wind, round_wind):
            yaku_list.append(Yaku("Pinfu", 1, closed_only=True))
        
        yakuhai_count = YakuChecker._check_yakuhai(hand, seat_wind, round_wind)
        for _ in range(yakuhai_count):
            yaku_list.append(Yaku("Yakuhai", 1))
        
        if YakuChecker._check_iipeikou(hand):
            yaku_list.append(Yaku("Iipeikou", 1, closed_only=True))
        
        if YakuChecker._check_toitoi(hand):
            yaku_list.append(Yaku("Toitoi", 2))
        
        if YakuChecker._check_honitsu(all_tiles):
            han = 3 if hand.is_closed() else 2
            yaku_list.append(Yaku("Honitsu", han))
        
        if YakuChecker._check_chinitsu(all_tiles):
            han = 6 if hand.is_closed() else 5
            yaku_list.append(Yaku("Chinitsu", han))
        
        # Add dora
        dora_count = YakuChecker._count_dora(all_tiles, dora_tiles)
        if hand.is_riichi and ura_dora_tiles:
            dora_count += YakuChecker._count_dora(all_tiles, ura_dora_tiles)
        
        if dora_count > 0:
            yaku_list.append(Yaku("Dora", dora_count))
        
        return yaku_list
    
    @staticmethod
    def _check_riichi(hand: Hand) -> bool:
        return hand.is_riichi
    
    @staticmethod
    def _check_menzen_tsumo(hand: Hand, is_tsumo: bool) -> bool:
        return hand.is_closed() and is_tsumo
    
    @staticmethod
    def _check_tanyao(tiles: List[Tile]) -> bool:
        """All simples - no terminals or honors"""
        return all(not tile.is_terminal_or_honor() for tile in tiles)
    
    @staticmethod
    def _check_pinfu(hand: Hand, winning_tile: Tile, seat_wind: Wind, round_wind: Wind) -> bool:
        """All sequences, no value pair, two-sided wait"""
        if not hand.is_closed():
            return False
        
        # Check all melds are sequences
        for meld in hand.melds:
            if not meld.is_sequence():
                return False
        
        # Find the pair
        tile_counts = {}
        for tile in hand.concealed_tiles:
            tile_counts[tile] = tile_counts.get(tile, 0) + 1
        
        pair_tile = None
        for tile, count in tile_counts.items():
            if count == 2:
                pair_tile = tile
                break
        
        if not pair_tile:
            return False
        
        # Check pair is not yakuhai
        if pair_tile.is_honor():
            if (pair_tile.suit == Suit.WIND and 
                (pair_tile.wind == seat_wind or pair_tile.wind == round_wind)):
                return False
            if pair_tile.suit == Suit.DRAGON:
                return False
        
        return True
    
    @staticmethod
    def _check_yakuhai(hand: Hand, seat_wind: Wind, round_wind: Wind) -> int:
        """Count yakuhai triplets"""
        count = 0
        for meld in hand.melds:
            if meld.is_triplet() or meld.is_kan():
                tile = meld.tiles[0]
                if tile.suit == Suit.DRAGON:
                    count += 1
                elif (tile.suit == Suit.WIND and 
                      (tile.wind == seat_wind or tile.wind == round_wind)):
                    count += 1
        return count
    
    @staticmethod
    def _check_iipeikou(hand: Hand) -> bool:
        """Same sequence twice, closed hand only"""
        if not hand.is_closed():
            return False
        
        sequences = [meld for meld in hand.melds if meld.is_sequence()]
        if len(sequences) < 2:
            return False
        
        for i, seq1 in enumerate(sequences):
            for seq2 in sequences[i+1:]:
                if sorted(seq1.tiles) == sorted(seq2.tiles):
                    return True
        return False
    
    @staticmethod
    def _check_toitoi(hand: Hand) -> bool:
        """All triplets plus a pair"""
        for meld in hand.melds:
            if not (meld.is_triplet() or meld.is_kan()):
                return False
        return True
    
    @staticmethod
    def _check_honitsu(tiles: List[Tile]) -> bool:
        """Half flush - one suit plus honors"""
        suits_present = set()
        has_honors = False
        
        for tile in tiles:
            if tile.is_honor():
                has_honors = True
            else:
                suits_present.add(tile.suit)
        
        return len(suits_present) == 1 and has_honors
    
    @staticmethod
    def _check_chinitsu(tiles: List[Tile]) -> bool:
        """Full flush - one suit only"""
        suits_present = set()
        
        for tile in tiles:
            if tile.is_honor():
                return False
            suits_present.add(tile.suit)
        
        return len(suits_present) == 1
    
    @staticmethod
    def _count_dora(tiles: List[Tile], dora_tiles: List[Tile]) -> int:
        """Count dora tiles in hand"""
        count = 0
        for tile in tiles:
            if tile in dora_tiles:
                count += 1
            if tile.is_red:  # Red fives are always dora
                count += 1
        return count
