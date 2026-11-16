"""Backtracking: systematic trial and error, written recursively.

The search tries a digit in an empty cell, recurses on the smaller puzzle,
and undoes the choice when it leads to a dead end.  Its correctness is a
proof by induction on the number of empty cells: a grid with no empty cells
is the base case, and each recursive call works on a grid with one fewer
empty cell.

`count_solutions` keeps searching after the first solution.  When it
explores the whole tree and finds exactly one, that is a proof by
exhaustion that the puzzle has a unique solution.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .board import CELLS, Grid, box_of

# Bits 1 through 9 are 1 and bit 0 is unused, so a digit d is the bit 1 << d.
# Example: digit 3 is the number 0b1000. Combining digits is then a bitwise OR.
ALL = 0b1111111110  # bits 1..9 set


@dataclass
class SearchResult:
    solution: Grid | None       # the first solution found, or None
    solutions_found: int        # how many were found before the limit
    nodes: int                  # recursive calls, one per partial grid
    backtracks: int             # cells where every digit failed
    seconds: float
    gave_up: bool = False       # True when the node limit stopped the search


class _Search:
    def __init__(self, grid: Grid, mrv: bool, limit: int, node_limit: int | None):
        self.mrv = mrv                  # pick the most constrained cell when True
        self.limit = limit              # stop after this many solutions
        self.node_limit = node_limit    # stop after this many nodes, or None
        # values[i] is the digit in CELLS[i]. Index i lines up with CELLS.
        self.values = [grid[cell] for cell in CELLS]
        # Bit masks of digits already used. Index 0 is unused so row 1 is rows[1].
        self.rows = [0] * 10
        self.cols = [0] * 10
        self.boxes = [0] * 10
        self.nodes = 0
        self.backtracks = 0
        self.found: list[list[int]] = []
        self.gave_up = False
        for i, (r, c) in enumerate(CELLS):
            d = self.values[i]
            if d:
                bit = 1 << d
                b = box_of((r, c))
                # AND with the bit is nonzero when that digit is already used.
                if (self.rows[r] | self.cols[c] | self.boxes[b]) & bit:
                    raise ValueError("the given clues break a Sudoku rule")
                # OR writes the bit into each of the three units.
                self.rows[r] |= bit
                self.cols[c] |= bit
                self.boxes[b] |= bit

    def options(self, i: int) -> int:
        """Bits of the digits still legal in cell i."""
        r, c = CELLS[i]
        # Used digits are the OR of the three units. NOT flips them, and AND
        # with ALL keeps only bits 1..9.
        return ALL & ~(self.rows[r] | self.cols[c] | self.boxes[box_of((r, c))])

    def choose_cell(self) -> int | None:
        """Index of the next empty cell, or None when the grid is full."""
        best, best_count = None, 10
        for i, d in enumerate(self.values):
            if d:
                continue
            if not self.mrv:
                return i  # first empty cell in reading order
            # bin(...).count("1") is the number of legal digits.
            count = bin(self.options(i)).count("1")
            if count < best_count:
                best, best_count = i, count
                if count <= 1:
                    break  # zero or one option cannot be beaten
        return best

    def run(self) -> None:
        if len(self.found) >= self.limit or self.gave_up:
            return
        self.nodes += 1
        if self.node_limit and self.nodes > self.node_limit:
            self.gave_up = True
            return
        i = self.choose_cell()
        if i is None:
            # Base case of the induction: no empty cells, so this is a solution.
            self.found.append(list(self.values))
            return
        r, c = CELLS[i]
        b = box_of((r, c))
        opts = self.options(i)
        for d in range(1, 10):
            bit = 1 << d
            if not opts & bit:
                continue  # this digit breaks a row, column, or box
            # Make the choice, then recurse on a grid with one fewer empty cell.
            self.values[i] = d
            self.rows[r] |= bit
            self.cols[c] |= bit
            self.boxes[b] |= bit
            self.run()
            # Undo the choice so the next digit is tried on the same grid.
            self.rows[r] &= ~bit
            self.cols[c] &= ~bit
            self.boxes[b] &= ~bit
            self.values[i] = 0
            if len(self.found) >= self.limit or self.gave_up:
                return
        # Every legal digit led to a dead end, so this partial grid fails.
        self.backtracks += 1


def _search(grid: Grid, mrv: bool, limit: int, node_limit: int | None) -> SearchResult:
    start = time.perf_counter()
    s = _Search(grid, mrv, limit, node_limit)
    s.run()
    solution = Grid(dict(zip(CELLS, s.found[0]))) if s.found else None
    return SearchResult(solution, len(s.found), s.nodes, s.backtracks,
                        time.perf_counter() - start, s.gave_up)


def solve_backtracking(grid: Grid, mrv: bool = True,
                       node_limit: int | None = None) -> SearchResult:
    """Find one solution.

    With `mrv` (Minimum Remaining Values) the search always branches on the
    empty cell with the fewest legal digits, the same choice a person makes
    when they look for the "most constrained" cell.  Without it, cells are
    filled in reading order.
    """
    return _search(grid, mrv, 1, node_limit)


def count_solutions(grid: Grid, limit: int = 2) -> SearchResult:
    """Count solutions, stopping once `limit` are found."""
    return _search(grid, True, limit, None)
