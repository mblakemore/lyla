import time

def calculate_pi(iterations=5000000):
    """Calculates Pi using the Leibniz series."""
    pi_over_4 = 0.0
    for i in range(iterations):
        term = (-1)**i / (2 * i + 1)
        pi_over_4 += term
    return pi_over_4 * 4

if __name__ == "__main__":
    start_time = time.perf_counter()
    result = calculate_pi()
    end_time = time.perf_counter()
    wallclock = (end_time - start_time) * 1000 # Convert to ms
    print(f"PI RESULT: {result}")
    print(f"WALLCLOCK TIME: {wallclock:.2f}ms")
