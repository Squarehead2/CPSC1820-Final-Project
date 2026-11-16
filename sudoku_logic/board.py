"""The Sudoku board described with sets and relations.

Rows, columns and digits all come from the set D = {1, ..., 9}.  A cell is an
ordered pair (r, c) in D x D, so the board is the Cartesian product of D with
itself and has |D x D| = 81 cells.

A *unit* is a set of 9 cells that must contain every digit exactly once
(a row, a column, or a 3x3 box).  Two different cells are *peers* when they
share a unit.  "Is a peer of" is a relation on the cells that is symmetric
and irreflexive, and every cell has exactly 20 peers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

DIGITS = frozenset(range(1, 10))
ROWS = range(1, 10)
COLS = range(1, 10)

Cell = tuple[int, int]

CELLS: list[Cell] = [(r, c) for r in ROWS for c in COLS]


def box_of(cell: Cell) -> int:
    """Box number 1..9, numbered left to right, top to bottom."""
    r, c = cell
    return 3 * ((r - 1) // 3) + (c - 1) // 3 + 1


def cell_name(cell: Cell) -> str:
    return f"R{cell[0]}C{cell[1]}"


@dataclass(frozen=True)
class Unit:
    kind: str  # "row", "column" or "box"
    index: int
    cells: frozenset[Cell] = field(compare=False)

    @property
    def name(self) -> str:
        return f"{self.kind} {self.index}"


ROW_UNITS = [Unit("row", r, frozenset((r, c) for c in COLS)) for r in ROWS]
COL_UNITS = [Unit("column", c, frozenset((r, c) for r in ROWS)) for c in COLS]
BOX_UNITS = [
    Unit("box", b, frozenset(cell for cell in CELLS if box_of(cell) == b))
    for b in range(1, 10)
]
UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS

UNITS_OF: dict[Cell, list[Unit]] = {
    cell: [u for u in UNITS if cell in u.cells] for cell in CELLS
}

PEERS: dict[Cell, frozenset[Cell]] = {
    cell: frozenset().union(*(u.cells for u in UNITS_OF[cell])) - {cell}
    for cell in CELLS
}


class Grid:
    """A (possibly partial) assignment of digits to cells. 0 means empty."""

    def __init__(self, values: dict[Cell, int] | None = None):
        self.values: dict[Cell, int] = {cell: 0 for cell in CELLS}
        if values:
            self.values.update(values)

    @classmethod
    def parse(cls, text: str) -> "Grid":
        """Read 81 symbols: digits 1-9 are givens, '0' or '.' are blanks.

        Any other characters (spaces, newlines, '|', '-', '+') are ignored so
        that both one-line strings and pretty-printed boards are accepted.
        """
        symbols = [ch for ch in text if ch.isdigit() or ch == "."]
        if len(symbols) != 81:
            raise ValueError(f"expected 81 cells, found {len(symbols)}")
        values = {
            cell: (0 if ch == "." else int(ch)) for cell, ch in zip(CELLS, symbols)
        }
        return cls(values)

    def copy(self) -> "Grid":
        return Grid(dict(self.values))

    def __getitem__(self, cell: Cell) -> int:
        return self.values[cell]

    def __setitem__(self, cell: Cell, digit: int) -> None:
        self.values[cell] = digit

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Grid) and self.values == other.values

    def givens(self) -> list[tuple[Cell, int]]:
        return [(cell, d) for cell, d in self.values.items() if d]

    def empty_cells(self) -> list[Cell]:
        return [cell for cell, d in self.values.items() if not d]

    def is_complete(self) -> bool:
        return all(self.values.values())

    def conflicts(self) -> list[tuple[Unit, int]]:
        """Every (unit, digit) pair where the digit appears more than once."""
        found = []
        for unit in UNITS:
            digits = [self.values[cell] for cell in unit.cells if self.values[cell]]
            for d in set(digits):
                if digits.count(d) > 1:
                    found.append((unit, d))
        return found

    def is_solved(self) -> bool:
        return self.is_complete() and not self.conflicts()

    def to_string(self) -> str:
        return "".join(str(self.values[cell]) if self.values[cell] else "." for cell in CELLS)

    def pretty(self) -> str:
        lines = []
        for r in ROWS:
            if r in (4, 7):
                lines.append("------+-------+------")
            row = []
            for c in COLS:
                if c in (4, 7):
                    row.append("|")
                d = self.values[(r, c)]
                row.append(str(d) if d else ".")
            lines.append(" ".join(row))
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.pretty()
