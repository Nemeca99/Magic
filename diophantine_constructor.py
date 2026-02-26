from __future__ import annotations

import argparse
import math
from typing import List, Sequence, Tuple, Dict

import magic


# Precomputed quadratic residues modulo 25 (squares mod 25)
SQUARE_RESIDUES_MOD_25 = {(n * n) % 25 for n in range(25)}
# Precomputed quadratic residues modulo 8 (squares mod 8)
SQUARE_RESIDUES_MOD_8 = {0, 1, 4}


def factor_int(n: int) -> Dict[int, int]:
    """
    Naive integer factorization by trial division.

    Returns a mapping prime -> exponent for |n|.
    """
    n = abs(n)
    factors: Dict[int, int] = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors[d] = factors.get(d, 0) + 1
            n //= d
        d = 3 if d == 2 else d + 2  # skip even numbers > 2
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def format_factors(factors: Dict[int, int]) -> str:
    """
    Format a prime factorization dictionary as a compact string, e.g. 2^4*3*5^2.
    """
    if not factors:
        return "1"
    parts: List[str] = []
    for p in sorted(factors.keys()):
        e = factors[p]
        if e == 1:
            parts.append(str(p))
        else:
            parts.append(f"{p}^{e}")
    return "*".join(parts)


def is_perfect_square(n: int) -> bool:
    if n <= 0:
        return False
    r = int(math.isqrt(n))
    return r * r == n


def square_pairs_for_center(C: int) -> List[Tuple[int, int]]:
    """
    For a given center C (itself a perfect square), find all ordered pairs
    of distinct perfect squares (a, b) such that:

        a + b = 2C
        a != b

    Returns pairs with a < b to keep the list canonical.
    """
    target = 2 * C
    pairs: List[Tuple[int, int]] = []

    # a and b are positive perfect squares strictly less than 2C
    max_root = int(math.isqrt(target - 1))
    for x in range(1, max_root + 1):
        a = x * x
        b = target - a
        if b <= 0:
            continue
        if not is_perfect_square(b):
            continue
        if a == b:
            continue
        if a > b:
            a, b = b, a
        pair = (a, b)
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def _all_distinct(values: Sequence[int]) -> bool:
    return len(set(values)) == len(values)


def _try_build_grids_from_pairs(
    C: int, pairs: Sequence[Tuple[int, int]]
) -> List[List[List[int]]]:
    """
    Given a list of candidate pairs (a,b) with a+b=2C, try to select four
    disjoint pairs and assign them to:

        (a, i), (c, g), (d, f), (b, h)

    Then construct 3x3 grids:

        a  b  c
        d  C  f
        g  h  i

    and validate them as magic squares using magic.is_magic.
    """
    from itertools import combinations, product, permutations

    solutions: List[List[List[int]]] = []

    # Choose 4 disjoint pairs (8 distinct squares)
    for four_pairs in combinations(pairs, 4):
        flat = [v for p in four_pairs for v in p]
        if not _all_distinct(flat):
            continue

        # Assign these 4 pairs to the 4 opposite positions around C
        for role_perm in permutations(four_pairs, 4):
            pair_ai, pair_cg, pair_df, pair_bh = role_perm

            # For each pair, we can flip which value sits on which side
            for flips in product([0, 1], repeat=4):
                a, i = pair_ai if flips[0] == 0 else (pair_ai[1], pair_ai[0])
                c, g = pair_cg if flips[1] == 0 else (pair_cg[1], pair_cg[0])
                d, f = pair_df if flips[2] == 0 else (pair_df[1], pair_df[0])
                b, h = pair_bh if flips[3] == 0 else (pair_bh[1], pair_bh[0])

                grid = [
                    [a, b, c],
                    [d, C, f],
                    [g, h, i],
                ]

                # All values must be distinct perfect squares
                flat_grid = [v for row in grid for v in row]
                if not _all_distinct(flat_grid):
                    continue
                if not all(is_perfect_square(v) for v in flat_grid):
                    continue

                if magic.is_magic(grid):
                    solutions.append(grid)
    return solutions


def _row_offsets_from_pairs(C: int, pairs: Sequence[Tuple[int, int]]) -> List[int]:
    """
    For each pair (a, b) with a + b = 2C, derive the normalized row offset
    Δ such that the row is [C-Δ, C, C+Δ].

    Since a^2 + c^2 = 2C implies (a^2 - C) = -(c^2 - C), each pair
    effectively gives one |Δ|. We return distinct non-zero Δ values.
    """
    deltas: List[int] = []
    for a, _b in pairs:
        # The constructor guarantees a + b = 2C; use the smaller as "left".
        delta = a - C
        if delta == 0:
            continue
        if delta not in deltas and -delta not in deltas:
            deltas.append(delta)
    return deltas


def _search_full_from_two_lines(C: int) -> None:
    """
    Given a center C and the sum-of-two-squares pairs a+b=2C, try to:

    - Choose a pair for the middle row (left/right),
    - Choose a (possibly different) pair for the middle column (top/bottom),
    - Use the forced corner formulas to obtain a,c,g,i,
    - Check if all 9 entries are distinct perfect squares.

    This is an algebraic reconstruction based on the 2-line configuration
    rather than a generic 4-pair search.
    """
    print(f"\n[FULL-2LINES] Center C = {C} (sqrt={int(math.isqrt(C))})")
    if not is_perfect_square(C):
        print("  C is not a perfect square; skipping.")
        return

    pairs = square_pairs_for_center(C)
    print(f"  Found {len(pairs)} distinct square pairs with a + b = 2C.")
    if not pairs:
        print("  No pairs -> cannot form even a single AP of squares.")
        return

    found_any = False
    from itertools import product

    for row_pair, col_pair in product(pairs, pairs):
        # Use smaller element as "left"/"top" for consistency
        row_left, row_right = sorted(row_pair)
        col_top, col_bottom = sorted(col_pair)

        # Quick distinctness / square checks on the 5 known positions
        base_vals = {C, row_left, row_right, col_top, col_bottom}
        if len(base_vals) != 5:
            continue
        if not all(is_perfect_square(v) for v in base_vals):
            continue

        # Derive corners via the algebraic formulas
        # Let x^2 = row_left, u^2 = col_top
        x2 = row_left
        u2 = col_top
        # d = (x^2 - u^2) / 2
        if (x2 - u2) % 2 != 0:
            continue
        d = (x2 - u2) // 2

        c = C + d
        g = C - d
        a = 2 * C - (x2 + u2) // 2
        i = (x2 + u2) // 2

        corners = [a, c, g, i]
        if not all(v > 0 for v in corners):
            continue
        if not all(is_perfect_square(v) for v in corners):
            continue

        # Full 3x3 candidate grid
        grid = [
            [a, col_top, c],
            [row_left, C, row_right],
            [g, col_bottom, i],
        ]
        flat = [v for row in grid for v in row]
        if len(set(flat)) != 9:
            continue

        # Final structural check via magic.is_magic (should hold if algebra is correct)
        if not magic.is_magic(grid):
            continue

        found_any = True
        print("\n  FOUND full 3x3 magic square of squares from two-line configuration:")
        magic.print_magic_square(grid)

    if not found_any:
        print("  No full 3x3 magic squares constructed from any two-line configuration.")


def check_corners_modular(C: int, dx: int, dy: int) -> None:
    """
    Given a center C and offsets dx, dy where the middle row is
    (C+dx, C, C-dx) and the middle column is (C+dy, C, C-dy),
    compute the four forced corners:

        a = C - dx - dy
        c = C + dx - dy
        g = C - dx + dy
        i = C + dx + dy

    Then:
      - Check if any are perfect squares (integer test),
      - Show their residues modulo 25 and whether those residues
        lie in the quadratic residue set modulo 25.

    If a corner has a non-square residue mod 25, it is provably
    not a perfect square.
    """
    print(f"\n[CORNER-CHECK] Center C = {C}, dx = {dx}, dy = {dy}")
    a = C - dx - dy
    c = C + dx - dy
    g = C - dx + dy
    i = C + dx + dy
    corners = [("a", a), ("c", c), ("g", g), ("i", i)]

    print("  Corner values and square tests:")
    for label, val in corners:
        is_sq = is_perfect_square(val)
        r25 = val % 25
        is_sq_mod25 = r25 in SQUARE_RESIDUES_MOD_25
        r8 = val % 8
        is_sq_mod8 = r8 in SQUARE_RESIDUES_MOD_8
        print(
            f"    {label}: {val} | sqrt int? {is_sq} | "
            f"mod 25 = {r25}, square-residue? {is_sq_mod25} | "
            f"mod 8 = {r8}, square-residue? {is_sq_mod8}"
        )


def log_corner_factors_for_center(C: int, k: int, fp) -> None:
    """
    For a given center C = k^2, find all two-line configurations (dx, dy)
    that yield five distinct perfect squares through the center, then:

      - Compute the four forced corners C±dx±dy,
      - Factor each corner,
      - Log prime factorizations and simple invariants to the file-like fp.
    """
    if not is_perfect_square(C):
        return

    pairs = square_pairs_for_center(C)
    if not pairs:
        return

    deltas = _row_offsets_from_pairs(C, pairs)
    if not deltas:
        return

    for dx in deltas:
        for dy in deltas:
            base_vals = {C, C - dx, C + dx, C - dy, C + dy}
            if len(base_vals) != 5:
                continue
            if not all(is_perfect_square(v) for v in base_vals):
                continue

            a = C - dx - dy
            c = C + dx - dy
            g = C - dx + dy
            i = C + dx + dy

            for label, val in (("a", a), ("c", c), ("g", g), ("i", i)):
                is_sq = is_perfect_square(val)
                r25 = val % 25
                r8 = val % 8
                factors = factor_int(val)
                has_odd_3mod4 = any(
                    (p % 4 == 3) and (e % 2 == 1) for p, e in factors.items()
                )
                factors_str = format_factors(factors)
                fp.write(
                    f"{k},{C},{dx},{dy},{label},{val},{is_sq},"
                    f"{r25},{r8},{has_odd_3mod4},{factors_str}\n"
                )

def analyze_two_lines(C: int) -> None:
    """
    Lighter normalization test:

    - Fix center C = k^2.
    - Use pairs with a + b = 2C to derive candidate offsets Δ for rows/cols:
        [C-Δ, C, C+Δ].
    - Look for choices (Δ_x, Δ_y) that give five distinct perfect squares:
        C, C±Δ_x, C±Δ_y.

    This tests whether a given center even supports two orthogonal
    arithmetic-progressions-of-squares through the same square center,
    before worrying about corners and diagonals.
    """
    print(f"\n[TWO-LINES] Analyzing center C = {C} (sqrt={int(math.isqrt(C))})")
    if not is_perfect_square(C):
        print("  C is not a perfect square; skipping.")
        return

    pairs = square_pairs_for_center(C)
    print(f"  Found {len(pairs)} distinct square pairs with a + b = 2C.")
    if not pairs:
        print("  No pairs -> no candidate offsets.")
        return

    deltas = _row_offsets_from_pairs(C, pairs)
    print(f"  Normalized offsets Delta available: {deltas if deltas else 'none'}")
    if len(deltas) < 1:
        print("  No non-zero offsets; cannot form even a single AP of squares.")
        return

    good_combos: List[Tuple[int, int]] = []
    for dx in deltas:
        for dy in deltas:
            # Allow dx == dy; distinctness check will filter invalid cases.
            vals = {C, C - dx, C + dx, C - dy, C + dy}
            if len(vals) != 5:
                continue
            if not all(is_perfect_square(v) for v in vals):
                continue
            good_combos.append((dx, dy))

    if not good_combos:
        print("  No (Delta_x, Delta_y) pairs yield five distinct square values.")
        return

    print(f"  FOUND {len(good_combos)} two-line configurations with 5 distinct squares:")
    for dx, dy in good_combos:
        vals = {
            "center": C,
            "row_left": C - dx,
            "row_right": C + dx,
            "col_top": C - dy,
            "col_bottom": C + dy,
        }
        print(f"    Delta_x={dx}, Delta_y={dy} -> {vals}")


def search_center(C: int) -> None:
    """
    Search for magic 3x3 squares of distinct perfect squares with center C
    using the Diophantine construction:

        - a + b = 2C for the 4 opposite pairs around the center
        - arrange into a 3x3 grid and validate with magic.is_magic
    """
    print(f"\n[CONSTRUCTOR] Searching center C = {C} (sqrt={int(math.isqrt(C))})")
    if not is_perfect_square(C):
        print("  C is not a perfect square; skipping.")
        return

    pairs = square_pairs_for_center(C)
    print(f"  Found {len(pairs)} distinct square pairs with a + b = 2C.")
    if len(pairs) < 4:
        print("  Not enough disjoint pairs to form a full 3x3 candidate.")
        return

    grids = _try_build_grids_from_pairs(C, pairs)
    if not grids:
        print("  No valid magic squares constructed from these pairs.")
        return

    print(f"  FOUND {len(grids)} magic square(s) for center C = {C}:")
    for idx, g in enumerate(grids, 1):
        print(f"\n  Solution #{idx}:")
        magic.print_magic_square(g)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diophantine constructor for 3x3 magic squares of distinct "
            "perfect squares with fixed center C = k^2."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--center",
        type=int,
        help="Explicit center C (must be a perfect square).",
    )
    group.add_argument(
        "--k",
        type=int,
        help="Center root k; searches C = k^2.",
    )
    group.add_argument(
        "--k-range",
        nargs=2,
        metavar=("K_MIN", "K_MAX"),
        type=int,
        help="Inclusive range of k; searches centers C = k^2 for each k.",
    )
    parser.add_argument(
        "--corner-check",
        action="store_true",
        help=(
            "With --center and --dx/--dy, check the four forced corners "
            "C±dx±dy for squarehood and modular obstructions."
        ),
    )
    parser.add_argument(
        "--dx",
        type=int,
        help="Row offset dx where row is (C+dx, C, C-dx).",
    )
    parser.add_argument(
        "--dy",
        type=int,
        help="Column offset dy where column is (C+dy, C, C-dy).",
    )
    parser.add_argument(
        "--two-lines",
        action="store_true",
        help=(
            "Instead of full 4-pair grid construction, only test whether a "
            "center supports two orthogonal 3-term APs of distinct squares "
            "through the center (row + column)."
        ),
    )
    parser.add_argument(
        "--full-from-two-lines",
        action="store_true",
        help=(
            "For each center, try to extend all two-line AP-of-squares "
            "configurations to a full 3x3 magic square by the forced "
            "corner formulas, and check if any yield 9 distinct squares."
        ),
    )
    parser.add_argument(
        "--log-corner-factors",
        action="store_true",
        help=(
            "With --k-range, log corner factorizations for all centers in "
            "the range that admit two-line AP-of-squares configurations."
        ),
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Optional output CSV file path for --log-corner-factors.",
    )

    args = parser.parse_args()

    if args.center is not None and args.corner_check:
        if args.dx is None or args.dy is None:
            raise SystemExit("corner-check requires --center, --dx, and --dy.")
        check_corners_modular(args.center, args.dx, args.dy)
        return

    # Corner factor logging over a k-range
    if args.k_range and getattr(args, "log_corner_factors", False):
        k_min, k_max = args.k_range
        if k_min > k_max:
            k_min, k_max = k_max, k_min
        out_path = getattr(args, "log_file", None) or f"corner_factors_{k_min}_{k_max}.csv"
        with open(out_path, "w", encoding="utf-8") as fp:
            fp.write(
                "k,C,dx,dy,label,corner,is_square,mod25,mod8,"
                "has_odd_prime_3mod4,factors\n"
            )
            for k in range(k_min, k_max + 1):
                C = k * k
                log_corner_factors_for_center(C, k, fp)
        return

    if args.center is not None:
        if args.full_from_two_lines:
            _search_full_from_two_lines(args.center)
        elif args.two_lines:
            analyze_two_lines(args.center)
        else:
            search_center(args.center)
        return

    if args.k is not None:
        C = args.k * args.k
        if args.full_from_two_lines:
            _search_full_from_two_lines(C)
        elif args.two_lines:
            analyze_two_lines(C)
        else:
            search_center(C)
        return

    if args.k_range:
        k_min, k_max = args.k_range
        if k_min > k_max:
            k_min, k_max = k_max, k_min
        for k in range(k_min, k_max + 1):
            C = k * k
            if args.full_from_two_lines:
                _search_full_from_two_lines(C)
            elif args.two_lines:
                analyze_two_lines(C)
            else:
                search_center(C)


if __name__ == "__main__":
    main()

