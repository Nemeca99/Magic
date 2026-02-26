import itertools
from multiprocessing import Pool, cpu_count
from functools import partial, lru_cache
from core_formulas_and_concepts import core_formulas

numbers = [i**2 for i in range(30, 81)]  # 30² to 80² (900 to 6400)

@lru_cache(maxsize=None)
def root(x):
    return x ** 0.5

@lru_cache(maxsize=None)
def int_root(x):
    return int(x ** 0.5)

def export_grid(grid, filename="magic_square_results.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write("┌──────┬──────┬──────┐\n")
        for i, row in enumerate(grid):
            f.write("│ " + " │ ".join(f"{x:4}" for x in row) + " │\n")
            if i < 2:
                f.write("├──────┼──────┼──────┤\n")
        f.write("└──────┴──────┴──────┘\n\n")

def print_roots(grid):
    print("Roots:")
    for row in grid:
        print(" ".join(f"{int_root(x):3}" for x in row))
    print()

fail_log: list = []

def root_triangle_check(grid, delta_tol=18):
    center = int_root(grid[1][1])
    deltas = [
        abs(center - int_root(grid[i][j]))
        for i in range(3) for j in range(3)
        if (i, j) != (1, 1)
    ]
    return max(deltas) - min(deltas) <= delta_tol

def is_phi_pair(a, b, phi_tol=0.05):
    root_a = root(a)
    root_b = root(b)
    if root_a + root_b == 0:
        return False
    ratio = max(root_a, root_b) / min(root_a, root_b)
    return abs(ratio - 1.618) < phi_tol or abs(ratio - 0.618) < phi_tol

def phi_cross_check(grid, phi_tol=0.05):
    return (
        is_phi_pair(grid[0][1], grid[2][1], phi_tol) and
        is_phi_pair(grid[1][0], grid[1][2], phi_tol)
    )

def row_root_energy(row):
    return sum(root(x) for x in row)

def curvature_balance(grid):
    energies = [
        row_root_energy(grid[0]),
        row_root_energy(grid[1]),
        row_root_energy(grid[2])
    ]
    return max(energies) - min(energies) < 1  # Arbitrary tolerance

def center_anchor_check(grid, target_center=None):
    if target_center is None:
        return True
    return grid[1][1] == target_center

def symmetry_score(grid):
    lines = [
        grid[0], grid[1], grid[2],  # rows
        [grid[0][0], grid[1][0], grid[2][0]],
        [grid[0][1], grid[1][1], grid[2][1]],
        [grid[0][2], grid[1][2], grid[2][2]],
        [grid[0][0], grid[1][1], grid[2][2]],
        [grid[0][2], grid[1][1], grid[2][0]],
    ]
    line_sums = [sum(line) for line in lines]
    return max(line_sums) - min(line_sums)

def print_magic_square(grid):
    print("┌──────┬──────┬──────┐")
    for i, row in enumerate(grid):
        print("│ " + " │ ".join(f"{x:4}" for x in row) + " │")
        if i < 2:
            print("├──────┼──────┼──────┤")
    print("└──────┴──────┴──────┘\n")

partial_results: list = []

def triangle_difference_harmony(grid):
    """
    Checks if the differences between center and adjacent root values form known triangle harmonics.
    Example sequences: [1,2,3], [3,6,9], [6,12,18], etc.
    """
    center = int_root(grid[1][1])
    # Cross positions: up, down, left, right
    cross_roots = [
        int_root(grid[0][1]),  # up
        int_root(grid[2][1]),  # down
        int_root(grid[1][0]),  # left
        int_root(grid[1][2]),  # right
    ]
    deltas = [abs(center - r) for r in cross_roots]
    deltas.sort()
    # Known harmonic sequences (expand as needed)
    known = [
        [1,2,3], [3,6,9], [6,12,18], [12,24,36],
        [6,6,12,12], [12,12,12,12], [6,6,6,6],
        [3,3,6,6], [2,4,6,8], [4,8,12,16]
    ]
    # Allow for tolerance in matching
    for seq in known:
        if len(seq) == len(deltas) and all(abs(a-b)<=1 for a,b in zip(seq, deltas)):
            return True
    return False

def ratio_based_diagonal_check(grid, tol=1.5):
    """
    Checks if diagonal root values are close to the geometric mean of center and cross roots.
    """
    center = root(grid[1][1])
    # Diagonals: TL-BR and TR-BL
    diag1 = root(grid[0][0])
    diag2 = root(grid[2][2])
    diag3 = root(grid[0][2])
    diag4 = root(grid[2][0])
    # Crosses
    up = root(grid[0][1])
    down = root(grid[2][1])
    left = root(grid[1][0])
    right = root(grid[1][2])
    # Geometric means
    gm1 = root(center * up)
    gm2 = root(center * down)
    gm3 = root(center * left)
    gm4 = root(center * right)
    # Check if diagonals are close to geometric means
    return (
        abs(diag1 - gm1) < tol and
        abs(diag2 - gm2) < tol and
        abs(diag3 - gm3) < tol and
        abs(diag4 - gm4) < tol
    )

def is_magic(grid):
    s = sum(grid[0])
    return (
        sum(grid[1]) == s and
        sum(grid[2]) == s and
        sum(grid[i][0] for i in range(3)) == s and
        sum(grid[i][1] for i in range(3)) == s and
        sum(grid[i][2] for i in range(3)) == s and
        sum(grid[i][i] for i in range(3)) == s and
        sum(grid[i][2-i] for i in range(3)) == s
    )

# Optimized check_magic with center lock, root caching, and short-circuiting
def check_magic(combo, target_center=None, delta_tol=18, phi_tol=0.05):
    # Precheck: total sum must be divisible by 3
    if sum(combo) % 3 != 0:
        return None
    # If center is locked, only permute combos with correct center
    if target_center is not None and target_center not in combo:
        return None
    # Fix center if specified, else try all possible centers
    centers = [target_center] if target_center is not None else combo
    for center in centers:
        # Remove center from combo for permutation
        rest = [x for x in combo if x != center]
        for perm in itertools.permutations(rest):
            # Build grid with center fixed
            grid = [
                [perm[0], perm[1], perm[2]],
                [perm[3], center, perm[4]],
                [perm[5], perm[6], perm[7]]
            ]
            magic_sum = sum(grid[0])
            # Fast line sum checks
            if (
                sum(grid[1]) != magic_sum or
                sum(grid[2]) != magic_sum or
                sum(grid[i][0] for i in range(3)) != magic_sum or
                sum(grid[i][1] for i in range(3)) != magic_sum or
                sum(grid[i][2] for i in range(3)) != magic_sum or
                sum(grid[i][i] for i in range(3)) != magic_sum or
                sum(grid[i][2-i] for i in range(3)) != magic_sum
            ):
                continue
            # Expensive checks only if line sums pass
            if not root_triangle_check(grid, delta_tol):
                continue
            if not phi_cross_check(grid, phi_tol):
                continue
            if not curvature_balance(grid):
                continue
            if not triangle_difference_harmony(grid):
                continue
            if not ratio_based_diagonal_check(grid):
                continue
            if not center_anchor_check(grid, target_center):
                continue
            export_grid(grid, filename="magic_square_results.txt")
            return grid
    return None

def print_core_formulas():
    print("\nCore Formulas and Concepts:")
    for name, formula, desc in core_formulas:
        print(f"- {name}: {formula}\n    {desc}")
    print()

def parity_type(a, b):
    if a % 2 == 0 and b % 2 == 0:
        return "Even-Even"
    elif a % 2 == 1 and b % 2 == 1:
        return "Odd-Odd"
    elif a % 2 == 0 and b % 2 == 1:
        return "Even-Odd"
    else:
        return "Odd-Even"

def print_parity_reflection(grid):
    print("Parity Reflection Outcomes:")
    # Rows
    for i, row in enumerate(grid):
        print(f"  Row {i+1}: {parity_type(int_root(row[0]), int_root(row[2]))}")
    # Columns
    for j in range(3):
        print(f"  Col {j+1}: {parity_type(int_root(grid[0][j]), int_root(grid[2][j]))}")
    # Diagonals
    print(f"  Diag TL-BR: {parity_type(int_root(grid[0][0]), int_root(grid[2][2]))}")
    print(f"  Diag TR-BL: {parity_type(int_root(grid[0][2]), int_root(grid[2][0]))}")
    print()

def print_root_energy_heatmap(grid):
    print("Grid Energy Map:")
    for row in grid:
        print("[ " + "  ".join(f"{int_root(x):2}" for x in row) + " ]")
    print()

def export_latex(grid, filename="magic_square_latex.tex"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\\begin{bmatrix}\n")
        for i, row in enumerate(grid):
            row_str = " & ".join(str(x) for x in row)
            f.write(f"  {row_str} \\\\n")
        f.write("\\end{bmatrix}\n")

MAGIC_SQUARE_PRINCIPLES = [
    "Recursive triangle symmetry",
    "Center-based ratio reflection logic",
    "Harmonic reasoning",
    "Parity triangle symmetry",
    "Magic constant (line sum): all rows, columns, and diagonals must sum to the same value",
    "Recursive harmonic reasoning",
    "Root triangle symmetry",
    "Ratio-based root triangles: diagonal root values as geometric means between center and cross",
    "Harmonic reflection rule: cross values reflect across center",
    "Triangle difference symmetry: differences between center and cross/diagonal roots must match known harmonic sequences",
    "Recursive root triangle alignment",
    "Line sum uniformity check",
    "Perfect square validation: n is a perfect square if √n is integer",
    "Delta/phi logic: golden ratio and delta tolerance checks",
    "Field closure, symmetry in curvature, resonant parity, and golden spiral balance across a compressed 3×3 grid"
]

def print_magic_square_principles():
    print("\nMagic Square of Squares: Harmonic & Recursive Principles")
    for p in MAGIC_SQUARE_PRINCIPLES:
        print(f"- {p}")
    print()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Search for a magic square of squares.")
    parser.add_argument('--workers', type=int, default=cpu_count(), help='Number of worker processes (default: all cores)')
    parser.add_argument('--center', type=int, default=None, help='Lock a specific value in the center square (optional)')
    parser.add_argument('--delta', type=int, default=18, help='Delta tolerance for root triangle check')
    parser.add_argument('--phi_tol', type=float, default=0.05, help='Tolerance for golden ratio checks')
    parser.add_argument('--roots_only', action='store_true', help='Only print square roots for output (no full grid formatting)')
    parser.add_argument('--max_score', type=int, default=10, help='Max symmetry score for partial or failed results')
    parser.add_argument('--latex', action='store_true', help='Export perfect solution as LaTeX bmatrix')
    args = parser.parse_args()

    print_magic_square_principles()
    print_core_formulas()
    combos = itertools.combinations(numbers, 9)
    print("Starting search for magic square of squares...")
    # Use partial to pass extra args to check_magic
    check_magic_partial = partial(
        check_magic,
        target_center=args.center,
        delta_tol=args.delta,
        phi_tol=args.phi_tol
    )
    found = False
    with Pool(args.workers) as pool:
        for idx, result in enumerate(pool.imap_unordered(check_magic_partial, combos)):
            if idx % 10000 == 0:
                print(f"Checked {idx} combinations...")
            if result:
                print("Magic square found:")
                if args.roots_only:
                    print_roots(result)
                else:
                    print_magic_square(result)
                    print_roots(result)
                    print_parity_reflection(result)
                    print_root_energy_heatmap(result)
                if args.latex:
                    export_latex(result)
                found = True
                pool.terminate()
                break
        if not found:
            print("No perfect magic square found.")
    # Print close-but-not-perfect candidates
    if partial_results:
        print("\nClose but imperfect candidates:")
        for grid in partial_results:
            if symmetry_score(grid) > args.max_score:
                continue
            if args.roots_only:
                print_roots(grid)
            else:
                print_magic_square(grid)
                print_roots(grid)
                print_parity_reflection(grid)
                print_root_energy_heatmap(grid)
    # Print failed but close candidates
    if fail_log:
        print("\nRejected close candidates:")
        for grid in fail_log:
            if symmetry_score(grid) > args.max_score:
                continue
            if args.roots_only:
                print_roots(grid)
            else:
                print_magic_square(grid)
                print_roots(grid)
                print_parity_reflection(grid)
                print_root_energy_heatmap(grid)