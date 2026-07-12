def calculate_average(numbers):
    """Return the average of a list of numbers.

    Args:
        numbers (list): A list of numeric values.

    Returns:
        float: The average of the numbers, or 0 if the list is empty.
    """
    if not numbers:
        return 0

    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)


if __name__ == "__main__":
    print(calculate_average([1, 2, 3, 4, 5]))
    print(calculate_average([]))
