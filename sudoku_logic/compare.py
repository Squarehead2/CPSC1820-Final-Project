"""Compare human-style deduction with systematic solving on the same puzzle."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .backtracking import count_solutions, solve_backtracking
from .board import Grid
from .deduction import solve_logically
from .sat import solve_sat

NAIVE_NODE_LIMIT = 200_000


@dataclass
class MethodReport:
    method: str
    solved: bool
    seconds: float
    work: str


def compare(grid: Grid) -> tuple[list[MethodReport], int]:
    """Run every method; also return the number of solutions (capped at 2)."""
    reports = []

    for label, use_contradiction in (("Logic: direct rules only", False),
                                     ("Logic: + proof by contradiction", True)):
        start = time.perf_counter()
        logic = solve_logically(grid, use_contradiction)
        counts = logic.rule_counts()
        work = f"{len(logic.steps)} steps"
        if counts:
            work += " (" + ", ".join(f"{rule}: {n}" for rule, n in counts.most_common()) + ")"
        if not logic.solved:
            work += f"; stuck with {81 - len(logic.grid.givens())} cells empty"
        reports.append(MethodReport(label, logic.solved, time.perf_counter() - start, work))

    for label, mrv, limit in (("Backtracking, reading order", False, NAIVE_NODE_LIMIT),
                              ("Backtracking, most constrained cell", True, None)):
        bt = solve_backtracking(grid, mrv=mrv, node_limit=limit)
        work = f"{bt.nodes:,} nodes, {bt.backtracks:,} dead ends"
        if bt.gave_up:
            work += f" (gave up after {limit:,} nodes)"
        reports.append(MethodReport(label, bt.solution is not None, bt.seconds, work))

    sat = solve_sat(grid)
    reports.append(MethodReport(
        "DPLL SAT solver on the CNF",
        sat.satisfiable,
        sat.seconds,
        f"{sat.decisions} guesses, {sat.propagations:,} unit propagations, "
        f"{sat.conflicts} failed branches",
    ))

    return reports, count_solutions(grid).solutions_found
