"""
number_pool.py — Modular Pool Configuration
"The Ghost of the Center" modding layer.

Edit this file to change the search space (Squares, Cubes, Primes, etc.)
"""

def get_number_pool():
    """
    Returns the list of integers to be used for the magic square search.
    
    MOD SECTIONS:
    - Squares (n=2): [i**2 for i in range(30, 81)]
    - Cubes (n=3):   [i**3 for i in range(1, 50)]
    - Primes:        [2, 3, 5, 7, 11...]
    """
    
    # DEFAULT: Squares (v3-v5 standard)
    return [i**2 for i in range(30, 81)]

# Metadata for UI
POOL_DESCRIPTION = "Squares (30^2 to 80^2)"
