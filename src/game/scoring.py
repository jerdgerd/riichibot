from typing import Dict, List, Optional, Tuple

from game.rules import Yaku
from game.hand import Hand
from tiles.tile import Suit, Tile, Wind


class Scoring:
    """Handle scoring calculations"""

    LIMIT_BASE_POINTS = {
        "mangan": 2000,
        "haneman": 3000,
        "baiman": 4000,
        "sanbaiman": 6000,
        "yakuman": 8000,
    }

    @staticmethod
    def calculate_score(
        yaku_list: List[Yaku],
        is_dealer: bool,
        is_tsumo: bool,
        *,
        hand: Optional[Hand] = None,
        winning_tile: Optional[Tile] = None,
        seat_wind: Optional[Wind] = None,
        round_wind: Optional[Wind] = None,
        fu: Optional[int] = None,
        honba: int = 0,
    ) -> Tuple[int, Dict[str, int]]:
        """Calculate final score and payments"""
        # Calculate total han
        total_han = sum(yaku.han for yaku in yaku_list)
        yakuman_count = Scoring._count_yakuman(yaku_list)

        if total_han == 0:
            raise ValueError("No yaku - cannot win")

        if yakuman_count > 0:
            base_points = Scoring.LIMIT_BASE_POINTS["yakuman"] * yakuman_count
        else:
            if fu is None:
                if hand and winning_tile and seat_wind and round_wind:
                    fu = Scoring.calculate_fu(
                        hand=hand,
                        winning_tile=winning_tile,
                        is_tsumo=is_tsumo,
                        seat_wind=seat_wind,
                        round_wind=round_wind,
                        yaku_list=yaku_list,
                    )
                else:
                    fu = 30

            base_points = Scoring._calculate_base_points(fu, total_han)

        # Calculate payments
        payments = {}
        if is_tsumo:
            if is_dealer:
                payment_per_player = Scoring._round_up_100(base_points * 2) + honba * 100
                payments = {"all": payment_per_player}
                final_score = payment_per_player * 3
            else:
                dealer_payment = Scoring._round_up_100(base_points * 2) + honba * 100
                non_dealer_payment = Scoring._round_up_100(base_points) + honba * 100
                payments = {
                    "dealer": dealer_payment,
                    "non_dealer": non_dealer_payment,
                }
                final_score = dealer_payment + non_dealer_payment * 2
        else:
            ron_multiplier = 6 if is_dealer else 4
            final_score = Scoring._round_up_100(base_points * ron_multiplier) + honba * 300
            payments = {"discarder": final_score}

        return final_score, payments

    @staticmethod
    def calculate_fu(
        hand: Hand,
        winning_tile: Tile,
        is_tsumo: bool,
        seat_wind: Wind,
        round_wind: Wind,
        yaku_list: List[Yaku],
    ) -> int:
        """Calculate fu for a completed hand."""
        yaku_names = {yaku.name for yaku in yaku_list}
        if "Kokushi Musou" in yaku_names:
            return 0
        if "Chiitoitsu" in yaku_names:
            return 25
        if "Pinfu" in yaku_names and is_tsumo:
            return 20

        tiles = hand.concealed_tiles[:]
        if len(tiles) == 13:
            tiles.append(winning_tile)

        decompositions = Scoring._decompose_standard_hand(tiles)
        if not decompositions:
            return 30

        base_fu = 20
        if is_tsumo and "Pinfu" not in yaku_names:
            base_fu += 2
        elif hand.is_closed():
            base_fu += 10

        open_meld_fu = sum(
            Scoring._meld_fu(meld.tiles, meld.is_open) for meld in hand.melds
        )

        max_fu = 0
        for melds, pair_tile in decompositions:
            fu = base_fu + open_meld_fu
            fu += Scoring._pair_fu(pair_tile, seat_wind, round_wind)
            fu += Scoring._meld_fu_total_with_win(melds, is_tsumo, winning_tile)

            if "Pinfu" not in yaku_names:
                fu += Scoring._wait_fu(pair_tile, melds, winning_tile)

            fu = Scoring._round_up_10(fu)
            if fu < 30:
                fu = 30
            max_fu = max(max_fu, fu)

        return max_fu

    @staticmethod
    def _calculate_base_points(fu: int, han: int) -> int:
        """Calculate base points with limit hands."""
        if han >= 13:
            return Scoring.LIMIT_BASE_POINTS["yakuman"]
        if han >= 11:
            return Scoring.LIMIT_BASE_POINTS["sanbaiman"]
        if han >= 8:
            return Scoring.LIMIT_BASE_POINTS["baiman"]
        if han >= 6:
            return Scoring.LIMIT_BASE_POINTS["haneman"]

        base = fu * (2 ** (han + 2))
        if han >= 5 or base >= Scoring.LIMIT_BASE_POINTS["mangan"]:
            return Scoring.LIMIT_BASE_POINTS["mangan"]

        return base

    @staticmethod
    def _round_up_100(points: int) -> int:
        return ((points + 99) // 100) * 100

    @staticmethod
    def _round_up_10(points: int) -> int:
        return ((points + 9) // 10) * 10

    @staticmethod
    def _meld_fu(meld_tiles: List[Tile], is_open: bool) -> int:
        if len(meld_tiles) not in (3, 4):
            return 0

        first_tile = meld_tiles[0]
        is_triplet = all(tile == first_tile for tile in meld_tiles)
        if not is_triplet:
            return 0

        is_terminal_or_honor = first_tile.is_terminal_or_honor()
        if len(meld_tiles) == 3:
            base = 2 if is_open else 4
        else:
            base = 8 if is_open else 16

        return base * (2 if is_terminal_or_honor else 1)

    @staticmethod
    def _meld_fu_total(melds: List[List[Tile]], is_open: bool) -> int:
        return sum(Scoring._meld_fu(meld, is_open) for meld in melds)

    @staticmethod
    def _meld_fu_total_with_win(
        melds: List[List[Tile]], is_tsumo: bool, winning_tile: Tile
    ) -> int:
        total = 0
        for meld in melds:
            is_open = False
            if (
                not is_tsumo
                and len(meld) in (3, 4)
                and all(tile == meld[0] for tile in meld)
                and winning_tile in meld
            ):
                is_open = True
            total += Scoring._meld_fu(meld, is_open=is_open)
        return total

    @staticmethod
    def _count_yakuman(yaku_list: List[Yaku]) -> int:
        """Count total yakuman multiples represented in yaku list."""
        count = 0
        for yaku in yaku_list:
            if yaku.name == "Dora":
                continue
            if yaku.han >= 13:
                count += max(1, yaku.han // 13)
        return count

    @staticmethod
    def _pair_fu(pair_tile: Tile, seat_wind: Wind, round_wind: Wind) -> int:
        fu = 0
        if pair_tile.suit == Suit.DRAGON:
            fu += 2
        elif pair_tile.suit == Suit.WIND:
            if pair_tile.wind == seat_wind:
                fu += 2
            if pair_tile.wind == round_wind:
                fu += 2
        return fu

    @staticmethod
    def _wait_fu(
        pair_tile: Tile, melds: List[List[Tile]], winning_tile: Tile
    ) -> int:
        if winning_tile == pair_tile:
            return 2

        wait_fu = 0
        for meld in melds:
            if winning_tile not in meld:
                continue
            if len(meld) != 3:
                continue
            if all(tile == meld[0] for tile in meld):
                continue

            seq = sorted(meld, key=lambda t: t.value or 0)
            if winning_tile == seq[1]:
                wait_fu = max(wait_fu, 2)
                continue

            low = seq[0].value
            high = seq[2].value
            if low == 1 and winning_tile == seq[2]:
                wait_fu = max(wait_fu, 2)
            elif high == 9 and winning_tile == seq[0]:
                wait_fu = max(wait_fu, 2)

        return wait_fu

    @staticmethod
    def _decompose_standard_hand(
        tiles: List[Tile],
    ) -> List[Tuple[List[List[Tile]], Tile]]:
        if len(tiles) != 14:
            return []

        results: List[Tuple[List[List[Tile]], Tile]] = []
        for pair_tile in set(tiles):
            if tiles.count(pair_tile) < 2:
                continue

            remaining = tiles[:]
            remaining.remove(pair_tile)
            remaining.remove(pair_tile)

            for melds in Scoring._extract_melds(remaining):
                results.append((melds, pair_tile))

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
            for melds in Scoring._extract_melds(remaining):
                results.append([[first, first, first]] + melds)

        if first.suit in (Suit.SOUZU, Suit.PINZU, Suit.MANZU) and first.value and first.value <= 7:
            tile2 = Tile(first.suit, first.value + 1)
            tile3 = Tile(first.suit, first.value + 2)
            if tile2 in tiles_sorted and tile3 in tiles_sorted:
                remaining = tiles_sorted[:]
                remaining.remove(first)
                remaining.remove(tile2)
                remaining.remove(tile3)
                for melds in Scoring._extract_melds(remaining):
                    results.append([[first, tile2, tile3]] + melds)

        return results
