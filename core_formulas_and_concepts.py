# Core formulas and concepts for Magic Square of Squares

core_formulas = [
    ("Keystone Parity Formula", "P = (T - C) / (2 × C)", "Determines recursive balance potential of a square field. T = total sum of square, C = center value. Used to find valid parity alignment."),
    ("Magic Constant (Line Sum)", "L = 3 × C", "Each row, column, and diagonal must sum to L. C is the center tile value for balanced reflection-based magic squares."),
    ("Triangle Difference Harmony", "Δ1, Δ2, Δ3 → Must match known triangle sequences like [1,2,3], [3,6,9]", "Checks if differences between center and adjacent root values form known triangle harmonics."),
    ("Ratio-Based Diagonal Estimation", "D ≈ √(C × X)", "Diagonal root values approximated as geometric means between center root (C) and a cross root (X)."),
    ("Harmonic Reflection Rule", "Cross Left < C < Cross Right, Bottom < C < Top (all even roots)", "Enforces mirror symmetry of even values around the center for cross axes."),
    ("Recursive Root Triangle Alignment", "Root(Center) ± Root(Cross) = Root(Diagonal) ± δ", "Diagonal values allowed to vary slightly (delta) to form recursive triangle mirrors with parity compensation."),
    ("Perfect Square Validation", "n is a perfect square if √n is integer", "Core validation for all 9 values in the grid. Ensures root integrity and uniqueness."),
    ("Line Sum Uniformity Check", "sum(row) = sum(col) = sum(diagonal) = L", "Confirms harmonic balance across all rows, columns, and diagonals of the square.")
]

parity_types = [
    ("Even-Even", "Occurs when both arms (e.g. cross or diagonal endpoints) are even. Creates inward reflection symmetry around an even center. Common in standard magic squares."),
    ("Odd-Odd", "Occurs when both outer values are odd. Forms inward difference tension around an odd or even center. Can create recursive compression fields."),
    ("Even-Odd", "Occurs when one value is even and the other is odd. Creates reflective imbalance that radiates outward. Often used to force triangle delta compensation on diagonals."),
    ("Odd-Even", "Mirrored form of Even-Odd, with imbalance initiated from the opposite direction. Completes field symmetry when used in diagonals or bottom/top cross arms.")
]

# Travis solution for reference
def get_travis_grid():
    return [
        [841, 1600, 1764],
        [576, 1296, 2304],
        [2116, 144, 1521]
    ]

def get_travis_roots():
    return [
        [29, 40, 42],
        [24, 36, 48],
        [46, 12, 39]
    ]
