from typing import Dict, List, Tuple

from game.player import Player
from game.rules import Yaku


class Scoring:
    """Handle scoring calculations"""

    BASE_POINTS = [
        (1, 1000),
        (2, 2000),
        (3, 3900),
        (4, 7700),
        (5, 8000),
        (6, 12000),
        (7, 12000),
        (8, 16000),
        (9, 16000),
        (10, 16000),
        (11, 24000),
        (12, 24000),
        (13, 32000),
    ]

    @staticmethod
    def calculate_score(
        yaku_list: List[Yaku], is_dealer: bool, is_tsumo: bool
    ) -> Tuple[int, Dict[str, int]]:
        """Calculate final score and payments"""
        # Calculate total han
        total_han = sum(yaku.han for yaku in yaku_list)

        if total_han == 0:
            raise ValueError("No yaku - cannot win")

        # Get base points
        base_points = Scoring._get_base_points(total_han)

        # Apply dealer multiplier
        if is_dealer:
            base_points = int(base_points * 1.5)

        # Round up to nearest 100
        final_score = ((base_points + 99) // 100) * 100

        # Calculate payments
        payments = {}
        if is_tsumo:
            if is_dealer:
                # All players pay equally
                payment_per_player = final_score // 3
                payments = {"all": payment_per_player}
            else:
                # Dealer pays half, others pay quarter each
                dealer_payment = final_score // 2
                non_dealer_payment = final_score // 4
                payments = {"dealer": dealer_payment, "non_dealer": non_dealer_payment}
        else:
            # Ron - discarding player pays all
            payments = {"discarder": final_score}

        return final_score, payments

    @staticmethod
    def _get_base_points(han: int) -> int:
        """Get base points for han count"""
        for h, points in Scoring.BASE_POINTS:
            if han <= h:
                return points
        return 32000  # Maximum
