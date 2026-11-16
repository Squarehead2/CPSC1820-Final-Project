"""Command-line interface for the Sudoku discrete-math project.

Examples:
    python main.py list
    python main.py rules
    python main.py encode easy --dimacs easy.cnf
    python main.py explain easy
    python main.py solve hard --method sat
    python main.py compare all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sudoku_logic.backtracking import count_solutions, solve_backtracking
from sudoku_logic.board import Grid
from sudoku_logic.compare import compare
from sudoku_logic.deduction import Contradiction, candidates_pretty, solve_logically
from sudoku_logic.logic import (
    PREDICATE_RULES,
    clause_str,
    counting_summary,
    encode,
    evaluate,
    grid_to_assignment,
    rule_cell,
)
from sudoku_logic.puzzles import PUZZLES
from sudoku_logic.sat import solve_sat


def load_puzzle(spec: str) -> tuple[str, Grid]:
    """A puzzle name from the library, a path to a text file, or 81 symbols."""
    if spec in PUZZLES:
        # Library entries are (description, grid text). Only the grid is parsed.
        return spec, Grid.parse(PUZZLES[spec][1])
    path = Path(spec)
    if path.is_file():
        return path.name, Grid.parse(path.read_text())
    # Last resort: treat the argument itself as the 81-character grid.
    return "custom", Grid.parse(spec)


def heading(text: str) -> None:
    """Print a title with a line of '=' under it."""
    print(f"\n{text}\n{'=' * len(text)}")


def side_by_side(left: Grid, right: Grid, gap: str = "      ") -> str:
    """Place two printed grids on one screen, clue grid then solved grid."""
    return "\n".join(a + gap + b for a, b in zip(left.pretty().splitlines(),
                                                   right.pretty().splitlines()))


def cmd_list(_args) -> None:
    """Print every sample puzzle with its clue count and why it is included."""
    heading("Sample puzzles")
    for name, (description, text) in PUZZLES.items():
        clues = sum(ch.isdigit() for ch in text)
        print(f"  {name:<8} {clues} clues  {description}")


def cmd_rules(_args) -> None:
    """Print the predicate-logic rules, one expanded clause, and the counts."""
    heading("Sudoku rules in predicate logic")
    print("Domain: r, c, n ∈ {1,...,9}.  P(r,c,n) = 'row r, column c holds digit n'.\n")
    for name, formula in PREDICATE_RULES.items():
        print(f"  {name:<30} {formula}")

    heading("From quantifiers to propositional clauses")
    print("Over a finite domain, ∃ becomes a disjunction and ∀ becomes a conjunction.")
    print("Example, 'R1C1 holds a digit' (∃n P(1,1,n)):")
    print(f"  {rule_cell((1, 1))}")
    print("Example, 'R1C1 does not hold both 1 and 2':")
    print("  ¬(P(1,1,1) ∧ P(1,1,2))  ≡  ¬P(1,1,1) ∨ ¬P(1,1,2)   (De Morgan's law)")

    heading("Counting the formula")
    for what, how, count in counting_summary():
        # 2^729 and 9^81 are too long to print, so show the power of ten instead.
        shown = f"{count:,}" if count < 10**12 else f"≈ 10^{len(str(count)) - 1}"
        print(f"  {what:<38} {how:<30} {shown}")


def cmd_encode(args) -> None:
    """Show how many clauses each rule produces, and optionally save DIMACS."""
    name, grid = load_puzzle(args.puzzle)
    cnf = encode(grid)
    heading(f"CNF encoding of '{name}'")
    for group, clauses in cnf.groups.items():
        print(f"  {group:<36} {len(clauses):>6,} clauses   e.g. {clause_preview(clauses)}")
    print(f"  {'total':<36} {len(cnf):>6,} clauses over 729 variables")
    if args.dimacs:
        Path(args.dimacs).write_text(cnf.to_dimacs())
        print(f"\nWrote DIMACS file to {args.dimacs}")


def clause_preview(clauses) -> str:
    """The first clause of a group, shortened so the table stays on one line."""
    if not clauses:
        return "-"
    text = clause_str(clauses[0])
    return text if len(text) < 60 else text[:57] + "..."


def cmd_explain(args) -> None:
    """Print the deduction proof, then the solved grid or the leftover candidates."""
    name, grid = load_puzzle(args.puzzle)
    heading(f"Step-by-step logical solution of '{name}'")
    print(grid.pretty())
    try:
        result = solve_logically(grid, use_contradiction=not args.no_contradiction)
    except Contradiction as reason:
        print(f"\nThe clues contradict each other: {reason}")
        return
    print()
    for i, step in enumerate(result.steps, 1):
        # --limit 0 is falsy, so 0 means "print every step".
        if args.limit and i > args.limit:
            print(f"... {len(result.steps) - args.limit} more steps (use --limit 0 to show all)")
            break
        print(f"{i:>3}. {step.describe()}")

    heading("Summary")
    for rule, count in result.rule_counts().most_common():
        print(f"  {rule:<18} {count}")
    if result.solved:
        print("\nSolved by deduction alone:\n")
        print(side_by_side(grid, result.grid))
    else:
        print("\nDeduction got stuck. Remaining candidates (pencil marks):\n")
        print(candidates_pretty(result.candidates))
        print("\nA systematic method (backtracking or SAT) is needed to finish.")


def cmd_solve(args) -> None:
    """Solve with one method, then model-check the answer and test uniqueness."""
    name, grid = load_puzzle(args.puzzle)
    heading(f"Solving '{name}' with method: {args.method}")
    if args.method == "logic":
        result = solve_logically(grid)
        solution = result.grid if result.solved else None
        print(f"{len(result.steps)} deduction steps")
    elif args.method == "backtrack":
        result = solve_backtracking(grid)
        solution = result.solution
        print(f"{result.nodes:,} search nodes, {result.backtracks:,} dead ends")
    else:
        result = solve_sat(grid)
        solution = result.grid()
        print(f"{result.decisions} decisions, {result.propagations:,} propagations")

    if solution is None:
        print("No complete solution found with this method.")
        return
    print()
    print(side_by_side(grid, solution))
    # Rebuild the CNF and check that the finished grid makes every clause true.
    violated = evaluate(encode(grid), grid_to_assignment(solution))
    print(f"\nModel check: {len(encode(grid)):,} clauses, {len(violated)} violated.")
    uniqueness = count_solutions(grid).solutions_found
    print("Uniqueness (exhaustive search):",
          "unique solution" if uniqueness == 1 else "more than one solution")


def cmd_compare(args) -> None:
    """Run every method. The puzzle argument "all" means the whole library."""
    names = list(PUZZLES) if args.puzzle == "all" else [args.puzzle]
    for spec in names:
        name, grid = load_puzzle(spec)
        heading(f"Comparing methods on '{name}' ({len(grid.givens())} clues)")
        reports, solutions = compare(grid)
        for r in reports:
            status = "solved" if r.solved else "not solved"
            print(f"  {r.method:<36} {status:<11} {r.seconds * 1000:>9.1f} ms   {r.work}")
        print(f"  Number of solutions: {'exactly 1' if solutions == 1 else 'at least 2'}")


def main(argv: list[str] | None = None) -> None:
    # The logic symbols (∀, ¬, ∨) need UTF-8. Windows consoles default to cp1252.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Sudoku through discrete mathematics.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show the sample puzzles").set_defaults(func=cmd_list)
    sub.add_parser("rules", help="show the rules in logic and count clauses").set_defaults(func=cmd_rules)

    p = sub.add_parser("encode", help="translate a puzzle into CNF")
    p.add_argument("puzzle", help="puzzle name, file, or 81-character string")
    p.add_argument("--dimacs", metavar="FILE", help="also write a DIMACS .cnf file")
    p.set_defaults(func=cmd_encode)

    p = sub.add_parser("explain", help="solve step by step with justifications")
    p.add_argument("puzzle")
    p.add_argument("--limit", type=int, default=40, help="max steps to print (0 = all)")
    p.add_argument("--no-contradiction", action="store_true",
                   help="only use direct rules, no proof by contradiction")
    p.set_defaults(func=cmd_explain)

    p = sub.add_parser("solve", help="solve with one method")
    p.add_argument("puzzle")
    p.add_argument("--method", choices=["logic", "backtrack", "sat"], default="sat")
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("compare", help="compare all methods")
    p.add_argument("puzzle", nargs="?", default="all")
    p.set_defaults(func=cmd_compare)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
