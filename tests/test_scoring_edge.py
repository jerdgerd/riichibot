"""
Extra edge-cases for Scoring base points and limit hands.
"""

import pytest

from src.game.scoring import Scoring


@pytest.mark.parametrize(
    "fu,han,expected",
    [
        (30, 1, 240),
        (30, 4, 1920),
        (40, 4, 2000),  # base exceeds mangan threshold
        (30, 5, 2000),
        (30, 6, 3000),
        (30, 8, 4000),
        (30, 11, 6000),
        (30, 13, 8000),
    ],
)
def test_base_point_table(fu, han, expected):
    pts = Scoring._calculate_base_points(fu, han)
    assert pts == expected
