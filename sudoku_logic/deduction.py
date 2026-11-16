"""Step-by-step logical deduction, the way a person solves Sudoku.

For every cell we track its *candidate set*: the digits n for which ¬P(r,c,n)
has not been proved yet.  Each technique below is an inference rule; it
either proves some P(r,c,n) (a placement) or proves some ¬P(r,c,n) (an
elimination).  Every step records which rule of inference justified it, so
the full solving process reads as a formal proof.

Techniques, from simplest to strongest:

* Naked single     - disjunctive syllogism on a cell's "at least one" clause.
* Hidden single    - disjunctive syllogism on a unit's "contains n" clause.
* Locked candidate - a unit's "contains n" clause can only be satisfied inside
                     a second unit, so n is eliminated from the rest of it.
* Naked pair       - proof by cases on two cells that share the same two
                     candidates.
* Contradiction    - proof by contradiction: assume P(r,c,n), derive a
                     contradiction using only singles, conclude ¬P(r,c,n).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .board import (
    BOX_UNITS,
    CELLS,
    COL_UNITS,
    DIGITS,
    PEERS,
    ROW_UNITS,
    UNITS,
    Cell,
    Grid,
    cell_name,
)


class Contradiction(Exception):
    """Raised when the current facts make some clause impossible to satisfy."""


def P(cell: Cell, n: int) -> str:
    return f"P({cell[0]},{cell[1]},{n})"


def notP(cell: Cell, n: int) -> str:
    return "¬" + P(cell, n)


@dataclass
class Step:
    rule: str
    explanation: str
    formal: str
    placement: tuple[Cell, int] | None = None
    eliminations: list[tuple[Cell, int]] = field(default_factory=list)

    def describe(self) -> str:
        lines = [f"[{self.rule}] {self.explanation}", f"    Logic: {self.formal}"]
        if self.eliminations:
            shown = ", ".join(notP(c, n) for c, n in self.eliminations[:6])
            more = len(self.eliminations) - 6
            if more > 0:
                shown += f", ... (+{more} more)"
            lines.append(f"    Therefore: {shown}")
        return "\n".join(lines)


@dataclass
class DeductionResult:
    grid: Grid
    steps: list[Step]
    solved: bool
    candidates: dict[Cell, set[int]]

    def rule_counts(self) -> Counter:
        return Counter(step.rule for step in self.steps)


class LogicalSolver:
    def __init__(self, grid: Grid, use_contradiction: bool = True):
        self.use_contradiction = use_contradiction
        self.candidates: dict[Cell, set[int]] = {cell: set(DIGITS) for cell in CELLS}
        self.solved: set[Cell] = set()
        self.steps: list[Step] = []
        for cell, n in grid.givens():
            self._place(cell, n)

    def _clone(self) -> "LogicalSolver":
        other = object.__new__(LogicalSolver)
        other.use_contradiction = False
        other.candidates = {cell: set(c) for cell, c in self.candidates.items()}
        other.solved = set(self.solved)
        other.steps = []
        return other

    # -- basic operations -------------------------------------------------

    def _place(self, cell: Cell, n: int) -> list[tuple[Cell, int]]:
        """Assert P(cell, n) and apply its consequences by modus ponens.

        From the "at most one digit" rule, P(r,c,n) → ¬P(r,c,m) for m ≠ n.
        From the "no repeats" rules, P(r,c,n) → ¬P(x,n) for every peer x.
        """
        if n not in self.candidates[cell]:
            raise Contradiction(f"{P(cell, n)} was already proved false")
        eliminated = [(cell, m) for m in sorted(self.candidates[cell] - {n})]
        self.candidates[cell] = {n}
        self.solved.add(cell)
        for peer in sorted(PEERS[cell]):
            if n in self.candidates[peer]:
                eliminated.append((peer, n))
                self._remove(peer, n)
        return eliminated

    def _remove(self, cell: Cell, n: int) -> None:
        self.candidates[cell].discard(n)
        if not self.candidates[cell]:
            raise Contradiction(f"{cell_name(cell)} has no digit left")

    def _check_units(self) -> None:
        for unit in UNITS:
            for n in DIGITS:
                if not any(n in self.candidates[c] for c in unit.cells):
                    raise Contradiction(f"{unit.name} has no place for {n}")

    def grid(self) -> Grid:
        return Grid({cell: next(iter(self.candidates[cell])) for cell in self.solved})

    def is_solved(self) -> bool:
        return len(self.solved) == 81

    # -- inference rules --------------------------------------------------

    def naked_single(self) -> bool:
        for cell in CELLS:
            if cell in self.solved or len(self.candidates[cell]) != 1:
                continue
            n = next(iter(self.candidates[cell]))
            others = sorted(DIGITS - {n})
            elim = self._place(cell, n)
            self.steps.append(Step(
                rule="Naked single",
                explanation=f"{cell_name(cell)} = {n}: every other digit is already ruled out for this cell.",
                formal=(
                    f"Cell rule P({cell[0]},{cell[1]},1) ∨ … ∨ P({cell[0]},{cell[1]},9), "
                    f"with ¬P for n ∈ {{{','.join(map(str, others))}}} ⊢ {P(cell, n)} "
                    f"(disjunctive syllogism)"
                ),
                placement=(cell, n),
                eliminations=elim,
            ))
            return True
        return False

    def hidden_single(self) -> bool:
        for unit in UNITS:
            for n in sorted(DIGITS):
                places = [c for c in unit.cells if n in self.candidates[c]]
                if len(places) == 0:
                    raise Contradiction(f"{unit.name} has no place for {n}")
                cell = places[0]
                if len(places) != 1 or cell in self.solved:
                    continue
                elim = self._place(cell, n)
                self.steps.append(Step(
                    rule="Hidden single",
                    explanation=f"{cell_name(cell)} = {n}: it is the only cell in {unit.name} that can hold {n}.",
                    formal=(
                        f"Unit rule ∃x ∈ {unit.name}: P(x,{n}), and ¬P(x,{n}) for the other 8 cells "
                        f"⊢ {P(cell, n)} (disjunctive syllogism)"
                    ),
                    placement=(cell, n),
                    eliminations=elim,
                ))
                return True
        return False

    def locked_candidates(self) -> bool:
        pairs = [(box, line) for box in BOX_UNITS for line in ROW_UNITS + COL_UNITS]
        for n in sorted(DIGITS):
            for a, b in pairs + [(line, box) for box, line in pairs]:
                if not a.cells & b.cells:
                    continue
                places = {c for c in a.cells if n in self.candidates[c]}
                if not places:
                    raise Contradiction(f"{a.name} has no place for {n}")
                if any(c in self.solved for c in places) or not places <= b.cells:
                    continue
                targets = sorted(c for c in b.cells - a.cells if n in self.candidates[c])
                if not targets:
                    continue
                for c in targets:
                    self._remove(c, n)
                self.steps.append(Step(
                    rule="Locked candidates",
                    explanation=(
                        f"In {a.name}, digit {n} can only go in cells that also lie in {b.name}, "
                        f"so {n} is removed from the rest of {b.name}."
                    ),
                    formal=(
                        f"{a.name} needs {n} (∃x ∈ {a.name}: P(x,{n})) and every option lies in {b.name}; "
                        f"{b.name} allows only one {n}, so ∀y ∈ {b.name} \\ {a.name}: ¬P(y,{n})"
                    ),
                    eliminations=[(c, n) for c in targets],
                ))
                return True
        return False

    def naked_pair(self) -> bool:
        for unit in UNITS:
            bivalue = [c for c in sorted(unit.cells)
                       if c not in self.solved and len(self.candidates[c]) == 2]
            for i, x in enumerate(bivalue):
                for y in bivalue[i + 1:]:
                    pair = self.candidates[x]
                    if self.candidates[y] != pair:
                        continue
                    a, b = sorted(pair)
                    targets = [(c, d) for c in sorted(unit.cells - {x, y})
                               for d in (a, b) if d in self.candidates[c]]
                    if not targets:
                        continue
                    for c, d in targets:
                        self._remove(c, d)
                    self.steps.append(Step(
                        rule="Naked pair",
                        explanation=(
                            f"{cell_name(x)} and {cell_name(y)} in {unit.name} can only be {a} or {b}, "
                            f"so those two digits are used up and removed from the rest of {unit.name}."
                        ),
                        formal=(
                            f"Proof by cases: ({P(x, a)} ∧ {P(y, b)}) ∨ ({P(x, b)} ∧ {P(y, a)}). "
                            f"In both cases {a} and {b} are taken in {unit.name}, so the other cells get ¬P"
                        ),
                        eliminations=targets,
                    ))
                    return True
        return False

    def contradiction(self) -> bool:
        """Assume a candidate, follow singles, and refute it if that fails.

        Cells with the fewest candidates are tried first, since a short
        disjunction is the most likely to produce a quick contradiction.
        """
        if not self.use_contradiction:
            return False
        open_cells = sorted((c for c in CELLS if c not in self.solved),
                            key=lambda c: len(self.candidates[c]))
        for cell in open_cells:
            for n in sorted(self.candidates[cell]):
                trial = self._clone()
                try:
                    trial._place(cell, n)
                    trial._run([trial.naked_single, trial.hidden_single])
                    trial._check_units()
                except Contradiction as reason:
                    self._remove(cell, n)
                    self.steps.append(Step(
                        rule="Contradiction",
                        explanation=(
                            f"Assume {cell_name(cell)} = {n}. Following only singles, "
                            f"{len(trial.steps)} steps later: {reason}. So {cell_name(cell)} ≠ {n}."
                        ),
                        formal=f"{P(cell, n)} → ⊥, therefore {notP(cell, n)} (proof by contradiction)",
                        eliminations=[(cell, n)],
                    ))
                    return True
        return False

    # -- driver -----------------------------------------------------------

    def _run(self, rules) -> None:
        while not self.is_solved():
            if not any(rule() for rule in rules):
                return

    def solve(self) -> DeductionResult:
        rules = [self.naked_single, self.hidden_single, self.locked_candidates,
                 self.naked_pair, self.contradiction]
        self._run(rules)
        return DeductionResult(self.grid(), self.steps, self.is_solved(),
                               {c: set(s) for c, s in self.candidates.items()})


def solve_logically(grid: Grid, use_contradiction: bool = True) -> DeductionResult:
    return LogicalSolver(grid, use_contradiction).solve()


def candidates_pretty(candidates: dict[Cell, set[int]]) -> str:
    """Pencil-mark view: each cell shows its remaining candidate digits."""
    width = max(len(c) for c in candidates.values())
    lines = []
    for r in range(1, 10):
        if r in (4, 7):
            lines.append("-" * (9 * (width + 1) + 4))
        row = []
        for c in range(1, 10):
            if c in (4, 7):
                row.append("|")
            row.append("".join(map(str, sorted(candidates[(r, c)]))).ljust(width))
        lines.append(" ".join(row))
    return "\n".join(lines)
