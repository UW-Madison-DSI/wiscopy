import pytest
from utilities import within


@pytest.mark.parametrize(
    "a, b, threshold",
    [
        (1.0, 1.0, 0.1),
        (1, 1, 0.1),
        (1e6, 1e7, 1e7),
    ]
)
def test_within_true(a, b, threshold):
    assert within(a, b, threshold)

@pytest.mark.parametrize(
    "a, b, threshold",
    [
        (1.0, 2.0, 0.1),
        (1, 2, 0.1),
        (1e6, 1e7, 1e6),
    ]
)
def test_within_false(a, b, threshold):
    assert not within(a, b, threshold)