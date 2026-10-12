def apply_discount(price: float, discount_percent: float) -> float:
    """Return a discounted price rounded to two decimal places."""
    return round(price * (1 - discount_percent / 100), 2)