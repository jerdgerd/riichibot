"""
Extra edge-cases for Scoring – exhaustive on low/hi han values.
"""

import pytest

from src.game.rules import Yaku
from src.game.scoring import Scoring


@pytest.mark.parametrize(
    "han,expected",
    [
        (1, 1000),
        (2, 2000),
        (3, 3900),
        (4, 7700),
        (5, 8000),
        (6, 12000),
        (11, 24000),
        (13, 32000),
    ],
)
def test_base_point_table(han, expected):
    pts = Scoring._get_base_points(han)
    assert pts == expected
