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
        # value[v] is True, False, or None (not decided yet). Index 0 is unused.
        self.value: list[bool | None] = [None] * (num_vars + 1)
        # Assignments in the order they were made, so a failed branch can be undone.
        self.trail: list[int] = []
        # occurs[literal] lists the clause indexes that contain that literal.
        self.occurs: dict[int, list[int]] = defaultdict(list)
        for i, clause in enumerate(clauses):
            for lit in clause:
                self.occurs[lit].append(i)
        # The "at least one" clauses are the only all-positive clauses longer
        # than one literal. Branching on those copies the "most constrained cell" idea.
        self.positive = [i for i, cl in enumerate(clauses)
                         if len(cl) > 1 and all(lit > 0 for lit in cl)]
        self.decisions = self.propagations = self.conflicts = 0

    def lit_value(self, lit: int) -> bool | None:
        """True, False, or None for one literal under the current assignment."""
        v = self.value[abs(lit)]
        return None if v is None else (v if lit > 0 else not v)

    def assign(self, lit: int) -> None:
        """Make this literal true and remember the variable so it can be undone."""
        self.value[abs(lit)] = lit > 0
        self.trail.append(abs(lit))

    def undo(self, mark: int) -> None:
        """Drop every assignment made after position `mark` on the trail."""
        while len(self.trail) > mark:
            self.value[self.trail.pop()] = None

    def propagate(self, queue: list[int]) -> bool:
        """Unit propagation. Returns False if some clause becomes false."""
        while queue:
            lit = queue.pop()
            # Only clauses that contain the opposite literal can newly become false.
            for ci in self.occurs[-lit]:
                unassigned, count = 0, 0
                for other in self.clauses[ci]:
                    v = self.lit_value(other)
                    if v is True:
                        break  # the clause is already satisfied
                    if v is None:
                        count += 1
                        unassigned = other
                        if count > 1:
                            break  # two open literals: not a unit clause yet
                else:
                    # The for-loop finished without finding a true literal.
                    if count == 0:
                        return False  # every literal is false: the clause is ⊥
                    # Exactly one literal is left, so it must be true.
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
                    break  # this clause is already true, so it is not a choice point
                if v is None:
                    open_lits.append(lit)
            else:
                # Still unsatisfied. Prefer the shortest remaining disjunction.
                if best_open is None or len(open_lits) < len(best_open):
                    best, best_open = ci, open_lits
                    if len(open_lits) == 2:
                        break  # length 2 is the shortest a non-unit clause can be
        return best_open[0] if best is not None else None

    def search(self) -> bool:
        lit = self.choose()
        if lit is None:
            return True  # no open clause left, so the assignment is a model
        self.decisions += 1
        # Proof by cases: the literal is true, or its negation is true.
        for attempt in (lit, -lit):
            mark = len(self.trail)
            self.assign(attempt)
            if self.propagate([attempt]) and self.search():
                return True
            self.conflicts += 1
            self.undo(mark)  # this case failed; restore the assignment
        return False  # both cases failed, so the earlier assumptions are wrong

    def solve(self) -> bool:
        queue = []
        for clause in self.clauses:
            if len(clause) == 1:
                # A unit clause is a premise: its single literal must be true.
                lit = clause[0]
                if self.lit_value(lit) is False:
                    return False  # two unit clauses contradict each other
                if self.lit_value(lit) is None:
                    self.assign(lit)
                    queue.append(lit)
        if not self.propagate(queue):
            return False  # the clues alone are unsatisfiable
        if not self.search():
            return False
        # Variables never forced either way can be false. For Sudoku that is
        # the digits a cell does not hold.
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
    """Encode the puzzle as CNF, then solve that formula."""
    return solve_cnf(encode(grid))
