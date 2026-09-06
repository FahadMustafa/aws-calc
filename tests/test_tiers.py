"""walk_tiers: tier-aware sum across priceDimensions bands."""
import pytest

from pricing_client import walk_tiers

# 0-10240 @ $0.09, 10240-51200 @ $0.085, 51200-Inf @ $0.07
BANDS = [
    {"begin_range": "0", "end_range": "10240", "price_per_unit": 0.09},
    {"begin_range": "10240", "end_range": "51200", "price_per_unit": 0.085},
    {"begin_range": "51200", "end_range": "Inf", "price_per_unit": 0.07},
]


@pytest.mark.parametrize(
    "gb, expected",
    [
        # nothing used, nothing charged
        (0, 0.0),
        # entirely inside band 1: 5000 * 0.09
        (5000, 450.0),
        # band 1 full + 9760 into band 2: 10240*0.09 + 9760*0.085
        (20000, 921.6 + 829.6),
        # bands 1 and 2 full + 48800 into the unbounded band:
        # 10240*0.09 + 40960*0.085 + 48800*0.07
        (100000, 921.6 + 3481.6 + 3416.0),
    ],
)
def test_walk_tiers(gb, expected):
    assert walk_tiers(gb, BANDS) == pytest.approx(expected)


def test_walk_tiers_ignores_dim_order():
    shuffled = [BANDS[2], BANDS[0], BANDS[1]]
    assert walk_tiers(20000, shuffled) == pytest.approx(walk_tiers(20000, BANDS))


def test_walk_tiers_single_unbounded_band():
    dims = [{"begin_range": "0", "end_range": "Inf", "price_per_unit": 0.023}]
    assert walk_tiers(1000, dims) == pytest.approx(23.0)


def test_walk_tiers_treats_blank_begin_range_as_zero():
    # the Pricing API sometimes returns an empty beginRange on the first band
    dims = [
        {"begin_range": "", "end_range": "10240", "price_per_unit": 0.09},
        {"begin_range": "10240", "end_range": "Inf", "price_per_unit": 0.085},
    ]
    assert walk_tiers(20000, dims) == pytest.approx(921.6 + 829.6)
