def within(a: int | float, b: int | float, threshold: int | float) -> bool:
    """Check if two values are within a certain range."""
    return abs(a - b) < threshold