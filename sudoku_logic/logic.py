"""Sudoku as propositional logic.

Proposition P(r, c, n) means "the cell in row r, column c contains digit n".
With r, c, n each in {1..9} there are 9^3 = 729 propositions.  Every rule of
Sudoku becomes a set of clauses (disjunctions of literals), and the whole
puzzle is their conjunction: a formula in Conjunctive Normal Form (CNF).
A filled-in grid is a solution exactly when the matching truth assignment
makes every clause true.

Literals are stored as integers in the DIMACS convention used by SAT
solvers: variable v is the literal +v and its negation is -v.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import comb

from .board import CELLS, DIGITS, UNITS, Cell, Grid

# A clause is a disjunction, stored as a tuple of integer literals.
Clause = tuple[int, ...]

# One Boolean variable for every triple (r, c, n).
NUM_VARS = 9 * 9 * 9


def var(r: int, c: int, n: int) -> int:
    """Bijection from {1..9}^3 to {1..729}: the variable number of P(r,c,n)."""
    # Layout: 81 variables per row, 9 per cell, then the digit 1..9.
    # Example: P(1,1,1) = 1 and P(1,1,2) = 2.
    return 81 * (r - 1) + 9 * (c - 1) + n


def unvar(v: int) -> tuple[int, int, int]:
    """Inverse of `var`."""
    v -= 1  # switch to a 0-based index so // and % split the number cleanly
    return v // 81 + 1, (v // 9) % 9 + 1, v % 9 + 1


def literal_str(lit: int) -> str:
    """Write +v as P(r,c,n) and -v as ¬P(r,c,n)."""
    r, c, n = unvar(abs(lit))
    return f"{'' if lit > 0 else '¬'}P({r},{c},{n})"


def clause_str(clause: Clause) -> str:
    """Join the literals with OR, since a clause is a disjunction."""
    return " ∨ ".join(literal_str(lit) for lit in clause)


PREDICATE_RULES = {
    "cell has a digit": "∀r ∀c ∃n P(r,c,n)",
    "cell has at most one digit": "∀r ∀c ∀n ∀m (n ≠ m → ¬(P(r,c,n) ∧ P(r,c,m)))",
    "row contains every digit": "∀r ∀n ∃c P(r,c,n)",
    "row has no repeats": "∀r ∀n ∀c ∀c' (c ≠ c' → ¬(P(r,c,n) ∧ P(r,c',n)))",
    "column contains every digit": "∀c ∀n ∃r P(r,c,n)",
    "column has no repeats": "∀c ∀n ∀r ∀r' (r ≠ r' → ¬(P(r,c,n) ∧ P(r',c,n)))",
    "box contains every digit": "∀b ∀n ∃(r,c) ∈ Box(b) P(r,c,n)",
    "box has no repeats": "∀b ∀n ∀x,y ∈ Box(b) (x ≠ y → ¬(P(x,n) ∧ P(y,n)))",
}


@dataclass
class CNF:
    """A formula in conjunctive normal form, with clauses grouped by rule."""

    groups: dict[str, list[Clause]] = field(default_factory=dict)

    @property
    def clauses(self) -> list[Clause]:
        # Flatten the groups. The formula is the conjunction of every clause.
        return [cl for group in self.groups.values() for cl in group]

    def __len__(self) -> int:
        return sum(len(g) for g in self.groups.values())

    def to_dimacs(self) -> str:
        """Standard DIMACS text, readable by any off-the-shelf SAT solver."""
        lines = [
            # Lines starting with "c" are comments. "p cnf" states the size.
            "c Sudoku encoded in CNF. Variable 81*(r-1) + 9*(c-1) + n is P(r,c,n).",
            f"p cnf {NUM_VARS} {len(self)}",
        ]
        # Each clause ends with 0, which is the DIMACS end-of-clause marker.
        lines += [" ".join(map(str, cl)) + " 0" for cl in self.clauses]
        return "\n".join(lines) + "\n"


def at_least_one(literals: list[int]) -> list[Clause]:
    """∃: a single disjunction  x1 ∨ x2 ∨ ... ∨ xk."""
    # One clause is enough: the disjunction is true when any literal is true.
    return [tuple(literals)]


def at_most_one(literals: list[int]) -> list[Clause]:
    """No two true at once: ¬(xi ∧ xj) ≡ ¬xi ∨ ¬xj for every pair i < j.

    This is the "pairwise" encoding and produces C(k, 2) clauses.
    """
    # combinations(literals, 2) lists every unordered pair exactly once.
    # Negating both literals forbids that pair from being true together.
    return [(-a, -b) for a, b in combinations(literals, 2)]


def sudoku_rules() -> CNF:
    """The 11,988 clauses that every Sudoku solution must satisfy."""
    cnf = CNF()
    cell_alo, cell_amo, unit_alo, unit_amo = [], [], [], []

    for r, c in CELLS:
        # The nine propositions "this cell holds n", one per digit.
        lits = [var(r, c, n) for n in sorted(DIGITS)]
        cell_alo += at_least_one(lits)  # the cell is not blank
        cell_amo += at_most_one(lits)   # the cell does not hold two digits

    for unit in UNITS:
        cells = sorted(unit.cells)
        for n in sorted(DIGITS):
            # The nine propositions "n sits in this cell of the unit".
            lits = [var(r, c, n) for r, c in cells]
            unit_alo += at_least_one(lits)  # the digit appears somewhere
            unit_amo += at_most_one(lits)   # the digit does not repeat

    cnf.groups["each cell has at least one digit"] = cell_alo
    cnf.groups["each cell has at most one digit"] = cell_amo
    cnf.groups["each unit contains every digit"] = unit_alo
    cnf.groups["no digit repeats in a unit"] = unit_amo
    return cnf


def encode(grid: Grid) -> CNF:
    """Rules plus one unit clause P(r,c,n) for each given clue."""
    cnf = sudoku_rules()
    # A unit clause (one literal) forces that proposition to be true.
    cnf.groups["given clues"] = [(var(r, c, n),) for (r, c), n in grid.givens()]
    return cnf


def grid_to_assignment(grid: Grid) -> dict[int, bool]:
    """Truth assignment for a completely filled grid."""
    # P(r,c,n) is true only for the digit actually written in that cell.
    return {
        var(r, c, n): grid[(r, c)] == n for (r, c) in CELLS for n in sorted(DIGITS)
    }


def assignment_to_grid(assignment: dict[int, bool]) -> Grid:
    grid = Grid()
    for v, value in assignment.items():
        if value:
            # Each true P(r,c,n) writes digit n into cell (r, c).
            r, c, n = unvar(v)
            grid[(r, c)] = n
    return grid


def evaluate(cnf: CNF, assignment: dict[int, bool]) -> list[tuple[str, Clause]]:
    """Model checking: return every clause the assignment makes false."""
    def lit_true(lit: int) -> bool:
        # A positive literal is true when its variable is true.
        # A negative literal is true when its variable is false.
        return assignment.get(abs(lit), False) == (lit > 0)

    return [
        (name, cl)
        for name, group in cnf.groups.items()
        for cl in group
        if not any(lit_true(lit) for lit in cl)  # a clause is false when every literal is false
    ]


def counting_summary() -> list[tuple[str, str, int]]:
    """How many clauses each rule produces, with the counting argument."""
    return [
        ("propositions P(r,c,n)", "9 · 9 · 9 = 9³", 9**3),
        ("cell: at least one digit", "81 cells · 1 clause", 81),
        ("cell: at most one digit", "81 cells · C(9,2)", 81 * comb(9, 2)),
        ("unit: contains every digit", "27 units · 9 digits", 27 * 9),
        ("unit: no repeats", "27 units · 9 digits · C(9,2)", 27 * 9 * comb(9, 2)),
        (
            "total rule clauses",
            "81 + 2916 + 243 + 8748",
            81 + 81 * comb(9, 2) + 27 * 9 + 27 * 9 * comb(9, 2),
        ),
        ("truth assignments to search naively", "2^729", 2**729),
        ("ways to fill 81 cells with digits", "9^81", 9**81),
    ]


def rule_cell(cell: Cell) -> str:
    """The 'at least one digit' clause for one cell, written out."""
    r, c = cell
    return clause_str(tuple(var(r, c, n) for n in sorted(DIGITS)))
