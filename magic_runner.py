from __future__ import annotations

import argparse
import sys
from typing import List

import power_modes


def _build_base_command(args: argparse.Namespace) -> List[str]:
    cmd: List[str] = ["python", "run_solver.py"]
    if args.mode:
        cmd += ["--mode", args.mode]
    if args.cores is not None:
        cmd += ["--cores", str(args.cores)]
    if args.resume:
        cmd += ["-resume", args.resume]
    return cmd


def _print_run_instructions(power: int, args: argparse.Namespace) -> None:
    mode = power_modes.get_power_mode(power)
    base_cmd = _build_base_command(args)
    base_cmd_str = " ".join(base_cmd)

    print("\n=== Magic Siege Runner ===")
    print(f" Power       : {mode.label}")
    print(f" Description : {mode.description}")
    print(f" Mode        : {args.mode}")
    print(f" Cores       : {args.cores}")
    if args.resume:
        print(f" Resume ID   : {args.resume}")

    print("\nThis helper does NOT auto-start the heavy GPU+CPU siege from the IDE.")
    print("Instead, run the solver from your own terminal with the environment set.")

    # Windows / PowerShell examples
    env_value = str(power)
    print("\nPowerShell example (recommended on Windows):")
    print(f'  $env:MAGIC_POWER="{env_value}"; {base_cmd_str}')

    print("\ncmd.exe example:")
    print(f'  set MAGIC_POWER={env_value} && {base_cmd_str}')

    print("\nPOSIX shell example (if running on WSL or Linux):")
    print(f"  MAGIC_POWER={env_value} {base_cmd_str}")

    print("\nThe solver will run n=1 foundation calibration internally before the main siege.")


def _run_calibration_here() -> int:
    """
    Optional light execution path: run only the n=1 foundation calibration.

    This uses the existing run_foundation_calibration from run_solver.py and
    does not start the full GPU+CPU combination siege.
    """
    import run_solver  # type: ignore

    ok = run_solver.run_foundation_calibration()
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Magic Siege Runner — n-aware helper around run_solver.py"
    )
    parser.add_argument(
        "--power",
        type=int,
        choices=sorted(power_modes.POWER_MODES.keys()),
        default=power_modes.DEFAULT_POWER,
        help="Search power n (1=baseline, 2=squares, 3=cubes).",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="science",
        choices=["science", "harmonic"],
        help="Search mode for run_solver.py.",
    )
    parser.add_argument(
        "--cores",
        type=int,
        default=16,
        help="CPU worker count for run_solver.py (default: 16).",
    )
    parser.add_argument(
        "-resume",
        type=str,
        default=None,
        help="Run ID to resume (same as run_solver.py -resume).",
    )
    parser.add_argument(
        "--execute-here",
        action="store_true",
        help=(
            "Run inside this process instead of printing commands. "
            "For safety, this only runs the n=1 foundation calibration."
        ),
    )

    args = parser.parse_args()

    if args.power == 1:
        if args.execute_here:
            # Light path: only foundation calibration, no full siege.
            return _run_calibration_here()
        else:
            # Even for n=1, default to instructions so the user stays in control.
            _print_run_instructions(args.power, args)
            print(
                "\nNote: n=1 calibration is much lighter, but this helper still avoids "
                "auto-running to keep control in your hands."
            )
            return 0

    # n=2 or n=3: always print safe instructions, never auto-run heavy siege here.
    _print_run_instructions(args.power, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

