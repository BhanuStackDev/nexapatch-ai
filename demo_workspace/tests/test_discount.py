from src.discount import apply_discount


def test_applies_percentage_discount() -> None:
    assert apply_discount(100.00, 10.0) == 90.00


def test_rounds_discounted_price_to_cents() -> None:
    assert apply_discount(19.99, 15.0) == 16.99