"""Compare human-style deduction with systematic solving on the same puzzle.

The five methods are the comparison the proposal asks for:
direct inference, inference plus proof by contradiction, backtracking in
reading order, backtracking on the most constrained cell, and DPLL.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .backtracking import count_solutions, solve_backtracking
from .board import Grid
from .deduction import solve_logically
from .sat import solve_sat

# Reading-order search can explode. Cap it so a comparison always finishes.
NAIVE_NODE_LIMIT = 200_000


@dataclass
class MethodReport:
    method: str     # label printed in the comparison table
    solved: bool
    seconds: float
    work: str       # steps, nodes, or guesses, depending on the method


def compare(grid: Grid) -> tuple[list[MethodReport], int]:
    """Run every method; also return the number of solutions (capped at 2)."""
    reports = []

    # Same solver twice: once without proof by contradiction, once with it.
    # The difference shows what that one inference rule adds.
    for label, use_contradiction in (("Logic: direct rules only", False),
                                     ("Logic: + proof by contradiction", True)):
        start = time.perf_counter()
        logic = solve_logically(grid, use_contradiction)
        counts = logic.rule_counts()
        work = f"{len(logic.steps)} steps"
        if counts:
            work += " (" + ", ".join(f"{rule}: {n}" for rule, n in counts.most_common()) + ")"
        if not logic.solved:
            # givens() here means "digits the deduction has proved", clues included.
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

    # Capped at 2: we only need to know whether the solution is unique.
    return reports, count_solutions(grid).solutions_found
