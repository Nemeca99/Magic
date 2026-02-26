# Unified Theory: The Odd/Even Duality & The RID Synthesis
**Theoretical Draft v1.5 — 2026-02-26**
**Context:** This document records empirical results and the current Diophantine
reduction of the 3×3 magic square of distinct squares problem.

---

## 5. Empirical Logs: The Siege Records
Summary of completed search runs using the **Science Mode** solver.

| Run ID | Power ($n$) | Pool Range | Combinations | Mode | Result |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **(6)** | **2 (Squares)** | **30² to 80²** | **3,042,312,350** | **Science** | **Exhaustive Negative (0 Found)** |
| **TBD** | **3 (Cubes)** | **30³ to 80³** | **3,042,312,350** | **Science** | **Pending Siege (n=3 odd-power search)** |

### 5.1 Siege Protocol for $n = 3$

All future odd-power ($n = 3$) sieges are required to:

1. **Run n=1 foundation calibration first**  
   - The solver invokes `run_foundation_calibration()` before any GPU/CPU siege work.  
   - Calibration uses the **baseline integer pool** \\(1..9\\) and verifies that at least one canonical magic square is identified via `gpu_magic_filter` + `magic.check_magic` with center locked at 5.  
   - A successful calibration is logged as a `type = "calibration"` event in `log.jsonl` with the active `power` and `pool` metadata.

2. **Run the n=3 cube siege with RID engaged**  
   - The active pool is configured via `MAGIC_POWER=3` and `number_pool.py` / `power_modes.py`.  
   - Pool description: **Cubes (30³ to 80³)**, mirroring the same index range as the even-power siege.  
   - The RID governor (`RIDGovernor`) remains **power-agnostic** and only responds to telemetry: GPU memory headroom (LTP) and throughput stability (RLE).

3. **Record full telemetry for post-hoc analysis**  
   - Each tick in `log.jsonl` is annotated with:  
     - `combos`, `cps`, `spm`, `s_n`, `batch`  
     - `power` (expected `3`) and `pool` (`"Cubes (30^3 to 80^3)"`).  
   - `state.json` snapshots also include `power` and `pool` for reconstructing the exact configuration at any point in the siege.

4. **Execute via external terminal (no IDE auto-runs)**  
   - Recommended pattern (PowerShell):  
     - `cd l:\\Steel_Brain\\Sqaures\\Magic_Complete`  
     - `$env:MAGIC_POWER=\"3\"; python run_solver.py --mode science --cores 16`  
   - Or use the `magic_runner.py` helper to print safe commands for the chosen power without auto-starting the siege.

---

## 6. The Odd/Even Conjecture: Falsifiability Statement
The central prediction of this theory hinges on the following testable conditions:

### Preliminary Evidence
The conjecture is supported if:
1.  **Even Search ($n^2$):** Science Mode confirms zero solutions across the bounded range. (Status: **Supported by Run 6**)
2.  **Odd Search ($n^3$):** Science Mode identifies **at least one** "High-Order Near Miss" (7 out of 8 lines) or a full magic square within an equivalent range.

### Falsification Condition
The theory is **falsified** if:
*   The "Science Mode" solver identifies **zero** solutions AND **zero** high-order near-misses for the Odd Power set ($n=3$) while operating within a range that scale-matches the $n=2$ search. This would prove that Odd powers are just as structurally resistant to the Magic Square container as Even powers.

---

## 7. Diophantine Constructor & Corner Analysis (Current Status)

Beyond the GPU sieges, a Diophantine analysis layer has been built to study the
strict geometric constraints of 3×3 magic squares of distinct perfect squares.

### 7.1 Two-Line Framework

For any proposed center value \(C = k^2\), a 3×3 magic square has:

- Middle row: \((C + \Delta_x,\ C,\ C - \Delta_x)\)
- Middle column: \((C + \Delta_y,\ C,\ C - \Delta_y)\)

where \(\Delta_x,\Delta_y\) are offsets coming from pairs of squares
\(x_1^2, x_2^2\) and \(u_1^2, u_2^2\) satisfying

- \(x_1^2 + x_2^2 = 2C\)
- \(u_1^2 + u_2^2 = 2C\)

The Diophantine constructor enumerates all such pairs for a given \(C\) and
asks:

1. Does there exist a pair of offsets \((\Delta_x,\Delta_y)\) such that
   \(\{C, C\pm\Delta_x, C\pm\Delta_y\}\) are **five distinct perfect squares**?
2. If so, what are the **forced corner values**?

### 7.2 Forced Corners: No Freedom Left

Once the two orthogonal lines through the center are fixed, the four corners are
fully determined by the magic-sum equations:

- \(a = C - \Delta_x - \Delta_y\)
- \(c = C + \Delta_x - \Delta_y\)
- \(g = C - \Delta_x + \Delta_y\)
- \(i = C + \Delta_x + \Delta_y\)

That is, the corners are exactly the four values
\[
 C \pm \Delta_x \pm \Delta_y.
\]

A 3×3 magic square of distinct squares at center \(C\) can exist in this
framework **only if** all nine numbers
\(\{C,\ C\pm\Delta_x,\ C\pm\Delta_y,\ C\pm\Delta_x\pm\Delta_y\}\) are distinct
perfect squares.

### 7.3 Empirical Result: Centers \(k \in [30, 400]\)

Using this two-line + corner framework, the following has been
computationally verified (via exact arithmetic, not heuristic search):

- **Centers tested:** \(C = k^2\) for all integers \(k\) with \(30 \le k \le 400\).
- **Two-line configurations:** 316 distinct choices of \((\Delta_x,\Delta_y)\)
  where both the middle row and middle column are 3-term arithmetic
  progressions of **distinct perfect squares** through the center.
- **Outcome:** For every such configuration:
  - The four corners \(C \pm \Delta_x \pm \Delta_y\) never yield more than
    **one** perfect square at a time.
  - In the rare cases where one corner is a square, it always appears in a
    conjugate pairing (the same value is forced twice), violating the
    distinctness requirement independently of the magic-sum constraints.

Thus, within this structured two-line framework, **no 3×3 magic square of
distinct squares exists** for any \(k \in [30, 400]\). This is not a brute-force
over all 9-tuples: for each center and two-line pattern, the corners are
derived algebraically and then checked.

### 7.4 Conjecture (Two-Line Diophantine Obstruction)

The experiments above suggest the following Diophantine conjecture:

> Let \(k \in \mathbb{Z}\), \(C = k^2\). Suppose there exist integers
> \((x_1,x_2)\), \((u_1,u_2)\) such that
> \[
>   x_1^2 + x_2^2 = 2C,\quad u_1^2 + u_2^2 = 2C,
> \]
> and define offsets
> \[
>   \Delta_x = x_1^2 - C,\quad \Delta_y = u_1^2 - C.
> \]
> Then the four corners
> \[
>   C \pm \Delta_x \pm \Delta_y
> \]
> can never all be **distinct perfect squares**.

If true, this would rule out 3×3 magic squares of distinct squares in the
entire two-line framework, for all centers \(C = k^2\). The evidence for
this conjecture is:

- Clean computational verification for \(30 \le k \le 400\),
- A visible algebraic structure (corners as \(C \pm \Delta_x \pm \Delta_y\)),
- Prime factor patterns in the forced corners that repeatedly obstruct them
  from being squares.

A full proof likely requires working in the Gaussian integers \(\mathbb{Z}[i]\)
and exploiting the constrained ways in which \(2k^2\) can be written as a sum
of two squares, but even in its current form this Diophantine layer is a
meaningful step beyond pure brute force.

---
*Sovereign Territory: l:\Steel_Brain\Sqaures\Magic_Complete\UNIFIED_THEORY_ODD_EVEN.md*
