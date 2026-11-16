"""A small DPLL SAT solver that works directly on the CNF formula.

DPLL (Davis-Putnam-Logemann-Loveland) mixes two ideas:

* Unit propagation - if every literal of a clause is false except one, that
  one must be true.  This is repeated resolution / modus ponens, and it is
  exactly the "naked single" and "hidden single" reasoning expressed on
  clauses instead of on a picture of the grid.
* Splitting - when propagation stalls, pick a variable, try it as true and
  then as false (proof by cases).  A branch that falsifies a clause is
  abandoned (proof by contradiction).

The solver knows nothing about rows, columns or boxes; everything it uses
is in the clauses produced by `logic.encode`.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass

from .board import Grid
from .logic import CNF, NUM_VARS, Clause, assignment_to_grid, encode


@dataclass
class SATResult:
    satisfiable: bool
    assignment: dict[int, bool] | None
    decisions: int
    propagations: int
    conflicts: int
    seconds: float

    def grid(self) -> Grid | None:
        return assignment_to_grid(self.assignment) if self.assignment else None


class DPLL:
    def __init__(self, clauses: list[Clause], num_vars: int):
        self.clauses = clauses
        self.num_vars = num_vars
        self.value: list[bool | None] = [None] * (num_vars + 1)
        self.trail: list[int] = []
        self.occurs: dict[int, list[int]] = defaultdict(list)
        for i, clause in enumerate(clauses):
            for lit in clause:
                self.occurs[lit].append(i)
        self.positive = [i for i, cl in enumerate(clauses)
                         if len(cl) > 1 and all(lit > 0 for lit in cl)]
        self.decisions = self.propagations = self.conflicts = 0

    def lit_value(self, lit: int) -> bool | None:
        v = self.value[abs(lit)]
        return None if v is None else (v if lit > 0 else not v)

    def assign(self, lit: int) -> None:
        self.value[abs(lit)] = lit > 0
        self.trail.append(abs(lit))

    def undo(self, mark: int) -> None:
        while len(self.trail) > mark:
            self.value[self.trail.pop()] = None

    def propagate(self, queue: list[int]) -> bool:
        """Unit propagation. Returns False if some clause becomes false."""
        while queue:
            lit = queue.pop()
            for ci in self.occurs[-lit]:
                unassigned, count = 0, 0
                for other in self.clauses[ci]:
                    v = self.lit_value(other)
                    if v is True:
                        break
                    if v is None:
                        count += 1
                        unassigned = other
                        if count > 1:
                            break
                else:
                    if count == 0:
                        return False
                    self.assign(unassigned)
                    self.propagations += 1
                    queue.append(unassigned)
        return True

    def choose(self) -> int | None:
        """Branch on the 'at least one' clause with the fewest open options."""
        best, best_open = None, None
        for ci in self.positive:
            open_lits = []
            for lit in self.clauses[ci]:
                v = self.lit_value(lit)
                if v is True:
                    break
                if v is None:
                    open_lits.append(lit)
            else:
                if best_open is None or len(open_lits) < len(best_open):
                    best, best_open = ci, open_lits
                    if len(open_lits) == 2:
                        break
        return best_open[0] if best is not None else None

    def search(self) -> bool:
        lit = self.choose()
        if lit is None:
            return True
        self.decisions += 1
        for attempt in (lit, -lit):
            mark = len(self.trail)
            self.assign(attempt)
            if self.propagate([attempt]) and self.search():
                return True
            self.conflicts += 1
            self.undo(mark)
        return False

    def solve(self) -> bool:
        queue = []
        for clause in self.clauses:
            if len(clause) == 1:
                lit = clause[0]
                if self.lit_value(lit) is False:
                    return False
                if self.lit_value(lit) is None:
                    self.assign(lit)
                    queue.append(lit)
        if not self.propagate(queue):
            return False
        if not self.search():
            return False
        for v in range(1, self.num_vars + 1):
            if self.value[v] is None:
                self.value[v] = False
        return True


def solve_cnf(cnf: CNF) -> SATResult:
    start = time.perf_counter()
    solver = DPLL(cnf.clauses, NUM_VARS)
    ok = solver.solve()
    assignment = {v: bool(solver.value[v]) for v in range(1, NUM_VARS + 1)} if ok else None
    return SATResult(ok, assignment, solver.decisions, solver.propagations,
                     solver.conflicts, time.perf_counter() - start)


def solve_sat(grid: Grid) -> SATResult:
    return solve_cnf(encode(grid))
