from dataclasses import dataclass
from typing import Dict, List, Optional

from game.hand import Hand, Meld
from tiles.tile import Dragon, Suit, Tile, Wind


@dataclass
class Yaku:
    name: str
    han: int
    closed_only: bool = False


class YakuChecker:
    """Check for yaku (winning conditions) in a hand"""

    @staticmethod
    def check_all_yaku(
        hand: Hand,
        winning_tile: Tile,
        is_tsumo: bool,
        seat_wind: Wind,
        round_wind: Wind,
        dora_tiles: List[Tile],
        ura_dora_tiles: List[Tile] = None,
    ) -> List[Yaku]:
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

        if YakuChecker._check_chiitoitsu(hand, winning_tile):
            yaku_list.append(Yaku("Chiitoitsu", 2, closed_only=True))

        if YakuChecker._check_kokushi(hand, winning_tile):
            yaku_list.append(Yaku("Kokushi Musou", 13, closed_only=True))

        yakuhai_count = YakuChecker._check_yakuhai(hand, seat_wind, round_wind, winning_tile)
        for _ in range(yakuhai_count):
            yaku_list.append(Yaku("Yakuhai", 1))

        if YakuChecker._check_iipeikou(hand, winning_tile):
            yaku_list.append(Yaku("Iipeikou", 1, closed_only=True))

        if YakuChecker._check_toitoi(hand, winning_tile):
            yaku_list.append(Yaku("Toitoi", 2))

        if YakuChecker._check_honitsu(all_tiles):
            han = 3 if hand.is_closed() else 2
            yaku_list.append(Yaku("Honitsu", han))

        if YakuChecker._check_chinitsu(all_tiles):
            han = 6 if hand.is_closed() else 5
            yaku_list.append(Yaku("Chinitsu", han))

        if YakuChecker._check_sanshoku_doujun(hand, winning_tile):
            yaku_list.append(Yaku("Sanshoku Doujun", 2 if hand.is_closed() else 1))

        if YakuChecker._check_ittsu(hand, winning_tile):
            yaku_list.append(Yaku("Ittsu", 2 if hand.is_closed() else 1))

        if YakuChecker._check_sanankou(hand, winning_tile, is_tsumo):
            yaku_list.append(Yaku("Sanankou", 2))

        if YakuChecker._check_chanta(hand, winning_tile):
            yaku_list.append(Yaku("Chanta", 2 if hand.is_closed() else 1))

        if YakuChecker._check_junchan(hand, winning_tile):
            yaku_list.append(Yaku("Junchan", 3 if hand.is_closed() else 2))

        if YakuChecker._check_honroutou(hand, winning_tile):
            yaku_list.append(Yaku("Honroutou", 2))

        if YakuChecker._check_shousangen(hand, winning_tile):
            yaku_list.append(Yaku("Shousangen", 2))

        if YakuChecker._check_daisangen(hand, winning_tile):
            yaku_list.append(Yaku("Daisangen", 13))

        if YakuChecker._check_suuankou(hand, winning_tile, is_tsumo):
            yaku_list.append(Yaku("Suuankou", 13, closed_only=True))

        if YakuChecker._check_suukantsu(hand):
            yaku_list.append(Yaku("Suukantsu", 13))

        if YakuChecker._check_tsuuiisou(hand, winning_tile):
            yaku_list.append(Yaku("Tsuuiisou", 13))

        if YakuChecker._check_chinroutou(hand, winning_tile):
            yaku_list.append(Yaku("Chinroutou", 13))

        if YakuChecker._check_ryuuiisou(hand, winning_tile):
            yaku_list.append(Yaku("Ryuuiisou", 13))

        if YakuChecker._check_chuuren_poutou(hand, winning_tile):
            yaku_list.append(Yaku("Chuuren Poutou", 13, closed_only=True))

        if YakuChecker._check_shousuushii(hand, winning_tile):
            yaku_list.append(Yaku("Shousuushii", 13))

        if YakuChecker._check_daisuushii(hand, winning_tile):
            yaku_list.append(Yaku("Daisuushii", 13))

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
    def _check_pinfu(
        hand: Hand, winning_tile: Tile, seat_wind: Wind, round_wind: Wind
    ) -> bool:
        """All sequences, no value pair, two-sided wait"""
        if not hand.is_closed():
            return False

        tiles = hand.concealed_tiles[:]
        if winning_tile not in tiles:
            tiles.append(winning_tile)

        if len(tiles) != 14:
            return False

        return YakuChecker._is_pinfu_hand(tiles, winning_tile, seat_wind, round_wind)

    @staticmethod
    def _is_pinfu_hand(
        tiles: List[Tile], winning_tile: Tile, seat_wind: Wind, round_wind: Wind
    ) -> bool:
        """Check if tiles can form pinfu with a ryanmen wait."""
        for pair_tile in set(tiles):
            if tiles.count(pair_tile) < 2:
                continue

            if pair_tile.is_honor():
                if pair_tile.suit == Suit.WIND and (
                    pair_tile.wind == seat_wind or pair_tile.wind == round_wind
                ):
                    continue
                if pair_tile.suit == Suit.DRAGON:
                    continue

            remaining = tiles[:]
            remaining.remove(pair_tile)
            remaining.remove(pair_tile)

            sequences: List[List[Tile]] = []
            if YakuChecker._extract_sequences(remaining, sequences):
                if YakuChecker._is_ryanmen_wait(
                    sequences, winning_tile
                ):
                    return True

        return False

    @staticmethod
    def _extract_sequences(tiles: List[Tile], sequences: List[List[Tile]]) -> bool:
        """Extract sequences only from tiles, recording a valid sequence set."""
        if not tiles:
            return True

        tiles.sort(key=lambda t: (t.suit.value, t.value or 0))
        first_tile = tiles[0]

        if first_tile.suit not in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            return False

        if first_tile.value is None or first_tile.value > 7:
            return False

        tile2 = Tile(first_tile.suit, first_tile.value + 1)
        tile3 = Tile(first_tile.suit, first_tile.value + 2)

        if tile2 in tiles and tile3 in tiles:
            tiles_copy = tiles[:]
            tiles_copy.remove(first_tile)
            tiles_copy.remove(tile2)
            tiles_copy.remove(tile3)
            sequences.append([first_tile, tile2, tile3])
            if YakuChecker._extract_sequences(tiles_copy, sequences):
                return True
            sequences.pop()

        return False

    @staticmethod
    def _is_ryanmen_wait(sequences: List[List[Tile]], winning_tile: Tile) -> bool:
        """Check if the winning tile completes a two-sided wait."""
        for sequence in sequences:
            if winning_tile not in sequence:
                continue

            seq = sorted(sequence, key=lambda t: t.value or 0)
            if winning_tile == seq[1]:
                return False  # middle tile -> kanchan wait

            low = seq[0].value
            high = seq[2].value
            if winning_tile == seq[2] and low == 1:
                return False  # 1-2-3 won on 3 -> edge wait
            if winning_tile == seq[0] and high == 9:
                return False  # 7-8-9 won on 7 -> edge wait

            return True

        return False

    @staticmethod
    def _check_chiitoitsu(hand: Hand, winning_tile: Tile) -> bool:
        """Check for seven pairs."""
        if not hand.is_closed():
            return False

        tiles = hand.concealed_tiles[:]
        if len(tiles) == 13:
            tiles.append(winning_tile)

        if len(tiles) != 14:
            return False

        pair_counts = [tiles.count(tile) for tile in set(tiles)]
        return len(pair_counts) == 7 and all(count == 2 for count in pair_counts)

    @staticmethod
    def _check_kokushi(hand: Hand, winning_tile: Tile) -> bool:
        """Check for thirteen orphans."""
        if not hand.is_closed():
            return False

        tiles = hand.concealed_tiles[:]
        if len(tiles) == 13:
            tiles.append(winning_tile)

        if len(tiles) != 14:
            return False

        terminals_and_honors = []
        for suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            terminals_and_honors.append(Tile(suit, 1))
            terminals_and_honors.append(Tile(suit, 9))

        for wind in Wind:
            terminals_and_honors.append(Tile(Suit.WIND, wind=wind))
        for dragon in Dragon:
            terminals_and_honors.append(Tile(Suit.DRAGON, dragon=dragon))

        unique_needed = set(terminals_and_honors)
        tile_set = set(tiles)
        if not unique_needed.issubset(tile_set):
            return False

        for tile in unique_needed:
            if tiles.count(tile) >= 2:
                return True

        return False


    @staticmethod
    def _check_yakuhai(
        hand: Hand, seat_wind: Wind, round_wind: Wind, winning_tile: Tile
    ) -> int:
        """Count yakuhai triplets"""
        def is_value_tile(tile: Tile) -> bool:
            if tile.suit == Suit.DRAGON:
                return True
            if tile.suit == Suit.WIND and (tile.wind == seat_wind or tile.wind == round_wind):
                return True
            return False
        max_count = 0
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            count = 0
            for meld in melds:
                if YakuChecker._is_triplet_meld(meld) and is_value_tile(meld[0]):
                    count += 1
            max_count = max(max_count, count)
        return max_count

    @staticmethod
    def _check_iipeikou(hand: Hand, winning_tile: Tile) -> bool:
        """Same sequence twice, closed hand only"""
        if not hand.is_closed():
            return False

        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            sequences = [meld for meld in melds if YakuChecker._is_sequence_meld(meld)]
            for i, seq1 in enumerate(sequences):
                for seq2 in sequences[i + 1 :]:
                    if sorted(seq1, key=lambda t: (t.suit.value, t.value or 0)) == sorted(
                        seq2, key=lambda t: (t.suit.value, t.value or 0)
                    ):
                        return True
        return False

    @staticmethod
    def _check_toitoi(hand: Hand, winning_tile: Tile) -> bool:
        """All triplets plus a pair"""
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            if all(
                YakuChecker._is_triplet_meld(meld)
                for meld in melds
            ):
                return True
        return False

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

    @staticmethod
    def _complete_hand_tiles(hand: Hand, winning_tile: Tile) -> List[Tile]:
        tiles = hand.get_all_tiles()
        if len(tiles) == 13:
            tiles = tiles[:] + [winning_tile]
        return tiles

    @staticmethod
    def _standard_decompositions(
        hand: Hand, winning_tile: Tile
    ) -> List[tuple[list[list[Tile]], Tile]]:
        fixed_melds = [meld.tiles[:] for meld in hand.melds]
        melds_needed = 4 - len(fixed_melds)
        concealed = hand.concealed_tiles[:]
        required_len = 2 + melds_needed * 3
        if len(concealed) == required_len - 1:
            concealed.append(winning_tile)
        if melds_needed < 0:
            return []
        if len(concealed) != 2 + melds_needed * 3:
            return []

        results: List[tuple[list[list[Tile]], Tile]] = []
        for pair_tile in set(concealed):
            if concealed.count(pair_tile) < 2:
                continue
            remaining = concealed[:]
            remaining.remove(pair_tile)
            remaining.remove(pair_tile)
            for melds in YakuChecker._extract_melds(remaining):
                if len(melds) != melds_needed:
                    continue
                results.append((fixed_melds + melds, pair_tile))
        return results

    @staticmethod
    def _extract_melds(tiles: List[Tile]) -> List[List[List[Tile]]]:
        if not tiles:
            return [[]]

        tiles_sorted = sorted(tiles, key=lambda t: (t.suit.value, t.value or 0))
        first = tiles_sorted[0]
        results: List[List[List[Tile]]] = []

        if tiles_sorted.count(first) >= 3:
            remaining = tiles_sorted[:]
            for _ in range(3):
                remaining.remove(first)
            for melds in YakuChecker._extract_melds(remaining):
                results.append([[first, first, first]] + melds)

        if first.suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU] and first.value and first.value <= 7:
            tile2 = Tile(first.suit, first.value + 1)
            tile3 = Tile(first.suit, first.value + 2)
            if tile2 in tiles_sorted and tile3 in tiles_sorted:
                remaining = tiles_sorted[:]
                remaining.remove(first)
                remaining.remove(tile2)
                remaining.remove(tile3)
                for melds in YakuChecker._extract_melds(remaining):
                    results.append([[first, tile2, tile3]] + melds)

        return results

    @staticmethod
    def _is_triplet_meld(meld: List[Tile]) -> bool:
        if len(meld) not in (3, 4):
            return False
        return all(tile == meld[0] for tile in meld)

    @staticmethod
    def _is_sequence_meld(meld: List[Tile]) -> bool:
        if len(meld) != 3:
            return False
        if meld[0].suit not in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
            return False
        seq = sorted(meld, key=lambda t: t.value or 0)
        return (
            seq[0].value is not None
            and seq[1].value == seq[0].value + 1
            and seq[2].value == seq[0].value + 2
        )

    @staticmethod
    def _check_sanshoku_doujun(hand: Hand, winning_tile: Tile) -> bool:
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            sequences = [
                meld
                for meld in melds
                if YakuChecker._is_sequence_meld(meld)
            ]
            for start in range(1, 8):
                suits = set()
                for meld in sequences:
                    seq = sorted(meld, key=lambda t: t.value or 0)
                    if seq[0].value == start:
                        suits.add(seq[0].suit)
                if len(suits) == 3:
                    return True
        return False

    @staticmethod
    def _check_ittsu(hand: Hand, winning_tile: Tile) -> bool:
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            sequences = [
                meld
                for meld in melds
                if YakuChecker._is_sequence_meld(meld)
            ]
            for suit in [Suit.SOUZU, Suit.PINZU, Suit.MANZU]:
                starts = {
                    sorted(meld, key=lambda t: t.value or 0)[0].value
                    for meld in sequences
                    if meld[0].suit == suit
                }
                if {1, 4, 7}.issubset(starts):
                    return True
        return False

    @staticmethod
    def _check_sanankou(hand: Hand, winning_tile: Tile, is_tsumo: bool) -> bool:
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            concealed_triplets = 0
            for meld in melds:
                if YakuChecker._is_triplet_meld(meld) and len(meld) == 3:
                    if not is_tsumo and winning_tile in meld:
                        continue
                    concealed_triplets += 1
                if YakuChecker._is_triplet_meld(meld) and len(meld) == 4:
                    concealed_triplets += 1
            if concealed_triplets >= 3:
                return True
        return False

    @staticmethod
    def _check_chanta(hand: Hand, winning_tile: Tile) -> bool:
        for melds, pair_tile in YakuChecker._standard_decompositions(hand, winning_tile):
            if not (pair_tile.is_terminal_or_honor()):
                continue
            has_sequence = False
            valid = True
            for meld in melds:
                if not any(tile.is_terminal_or_honor() for tile in meld):
                    valid = False
                    break
                if YakuChecker._is_sequence_meld(meld):
                    has_sequence = True
            if valid and has_sequence:
                return True
        return False

    @staticmethod
    def _check_junchan(hand: Hand, winning_tile: Tile) -> bool:
        for melds, pair_tile in YakuChecker._standard_decompositions(hand, winning_tile):
            if pair_tile.is_honor() or not pair_tile.is_terminal():
                continue
            has_sequence = False
            valid = True
            for meld in melds:
                if any(tile.is_honor() for tile in meld):
                    valid = False
                    break
                if not any(tile.is_terminal() for tile in meld):
                    valid = False
                    break
                if YakuChecker._is_sequence_meld(meld):
                    has_sequence = True
            if valid and has_sequence:
                return True
        return False

    @staticmethod
    def _check_honroutou(hand: Hand, winning_tile: Tile) -> bool:
        tiles = YakuChecker._complete_hand_tiles(hand, winning_tile)
        if not all(tile.is_terminal_or_honor() for tile in tiles):
            return False
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            if all(YakuChecker._is_triplet_meld(meld) and len(meld) == 3 for meld in melds):
                return True
        return False

    @staticmethod
    def _check_shousangen(hand: Hand, winning_tile: Tile) -> bool:
        for melds, pair_tile in YakuChecker._standard_decompositions(hand, winning_tile):
            if pair_tile.suit != Suit.DRAGON:
                continue
            dragon_triplets = 0
            for meld in melds:
                if len(meld) >= 3 and meld[0] == meld[1] == meld[2] and meld[0].suit == Suit.DRAGON:
                    dragon_triplets += 1
            if dragon_triplets == 2:
                return True
        return False

    @staticmethod
    def _check_daisangen(hand: Hand, winning_tile: Tile) -> bool:
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            dragon_triplets = 0
            for meld in melds:
                if len(meld) >= 3 and meld[0] == meld[1] == meld[2] and meld[0].suit == Suit.DRAGON:
                    dragon_triplets += 1
            if dragon_triplets == 3:
                return True
        return False

    @staticmethod
    def _check_suuankou(hand: Hand, winning_tile: Tile, is_tsumo: bool) -> bool:
        if not hand.is_closed():
            return False
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            triplets = 0
            for meld in melds:
                if len(meld) == 3 and meld[0] == meld[1] == meld[2]:
                    if not is_tsumo and winning_tile in meld:
                        continue
                    triplets += 1
                if len(meld) == 4 and meld[0] == meld[1] == meld[2] == meld[3]:
                    triplets += 1
            if triplets == 4:
                return True
        return False

    @staticmethod
    def _check_suukantsu(hand: Hand) -> bool:
        return sum(1 for meld in hand.melds if meld.is_kan()) == 4

    @staticmethod
    def _check_tsuuiisou(hand: Hand, winning_tile: Tile) -> bool:
        tiles = YakuChecker._complete_hand_tiles(hand, winning_tile)
        return all(tile.is_honor() for tile in tiles)

    @staticmethod
    def _check_chinroutou(hand: Hand, winning_tile: Tile) -> bool:
        tiles = YakuChecker._complete_hand_tiles(hand, winning_tile)
        return all(tile.is_terminal() for tile in tiles)

    @staticmethod
    def _check_ryuuiisou(hand: Hand, winning_tile: Tile) -> bool:
        green_tiles = {
            Tile(Suit.SOUZU, 2),
            Tile(Suit.SOUZU, 3),
            Tile(Suit.SOUZU, 4),
            Tile(Suit.SOUZU, 6),
            Tile(Suit.SOUZU, 8),
            Tile(Suit.DRAGON, dragon=Dragon.GREEN),
        }
        tiles = YakuChecker._complete_hand_tiles(hand, winning_tile)
        return all(tile in green_tiles for tile in tiles)

    @staticmethod
    def _check_chuuren_poutou(hand: Hand, winning_tile: Tile) -> bool:
        if not hand.is_closed():
            return False
        tiles = YakuChecker._complete_hand_tiles(hand, winning_tile)
        if len(tiles) != 14:
            return False
        if any(tile.is_honor() for tile in tiles):
            return False
        suits = {tile.suit for tile in tiles}
        if len(suits) != 1:
            return False
        counts = {i: 0 for i in range(1, 10)}
        for tile in tiles:
            counts[tile.value] += 1
        base = [1, 1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9]
        required = {1: 3, 9: 3, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1}
        if any(counts[num] < req for num, req in required.items()):
            return False
        extra = sum(counts.values()) - sum(required.values())
        return extra == 1

    @staticmethod
    def _check_shousuushii(hand: Hand, winning_tile: Tile) -> bool:
        for melds, pair_tile in YakuChecker._standard_decompositions(hand, winning_tile):
            wind_triplets = 0
            for meld in melds:
                if len(meld) >= 3 and meld[0] == meld[1] == meld[2] and meld[0].suit == Suit.WIND:
                    wind_triplets += 1
            if wind_triplets == 3 and pair_tile.suit == Suit.WIND:
                return True
        return False

    @staticmethod
    def _check_daisuushii(hand: Hand, winning_tile: Tile) -> bool:
        for melds, _ in YakuChecker._standard_decompositions(hand, winning_tile):
            wind_triplets = 0
            for meld in melds:
                if len(meld) >= 3 and meld[0] == meld[1] == meld[2] and meld[0].suit == Suit.WIND:
                    wind_triplets += 1
            if wind_triplets == 4:
                return True
        return False
