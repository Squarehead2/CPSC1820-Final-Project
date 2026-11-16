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

# D = {1, ..., 9}. A frozenset cannot be changed, which matches a fixed domain.
DIGITS = frozenset(range(1, 10))
ROWS = range(1, 10)
COLS = range(1, 10)

# A cell is an ordered pair (row, column), so the type is an element of D x D.
Cell = tuple[int, int]

# The board is the Cartesian product D x D, listed row by row. |D x D| = 81.
CELLS: list[Cell] = [(r, c) for r in ROWS for c in COLS]


def box_of(cell: Cell) -> int:
    """Box number 1..9, numbered left to right, top to bottom."""
    r, c = cell
    # Integer division by 3 groups rows 1-3, 4-6, and 7-9 into bands 0, 1, 2.
    # Multiplying the band by 3 and adding the column group gives boxes 1..9.
    return 3 * ((r - 1) // 3) + (c - 1) // 3 + 1


def cell_name(cell: Cell) -> str:
    """Readable name used in proofs, for example R5C2 for row 5, column 2."""
    return f"R{cell[0]}C{cell[1]}"


@dataclass(frozen=True)
class Unit:
    kind: str  # "row", "column" or "box"
    index: int
    # compare=False: two units with the same kind and index are equal even if
    # their cell sets were built separately.
    cells: frozenset[Cell] = field(compare=False)

    @property
    def name(self) -> str:
        return f"{self.kind} {self.index}"


# A row is the set of cells that share a row number. Same idea for columns.
ROW_UNITS = [Unit("row", r, frozenset((r, c) for c in COLS)) for r in ROWS]
COL_UNITS = [Unit("column", c, frozenset((r, c) for r in ROWS)) for c in COLS]
# Each box is the set of cells whose box_of value equals that box number.
BOX_UNITS = [
    Unit("box", b, frozenset(cell for cell in CELLS if box_of(cell) == b))
    for b in range(1, 10)
]
# 9 rows + 9 columns + 9 boxes = 27 units.
UNITS = ROW_UNITS + COL_UNITS + BOX_UNITS

# Each cell belongs to exactly three units: its row, its column, and its box.
UNITS_OF: dict[Cell, list[Unit]] = {
    cell: [u for u in UNITS if cell in u.cells] for cell in CELLS
}

# Peers of a cell = (union of its three units) minus the cell itself.
# A cell is never its own peer, so the relation is irreflexive.
PEERS: dict[Cell, frozenset[Cell]] = {
    cell: frozenset().union(*(u.cells for u in UNITS_OF[cell])) - {cell}
    for cell in CELLS
}


class Grid:
    """A (possibly partial) assignment of digits to cells. 0 means empty."""

    def __init__(self, values: dict[Cell, int] | None = None):
        # Start from the empty function (every cell maps to 0), then overlay clues.
        self.values: dict[Cell, int] = {cell: 0 for cell in CELLS}
        if values:
            self.values.update(values)

    @classmethod
    def parse(cls, text: str) -> "Grid":
        """Read 81 symbols: digits 1-9 are givens, '0' or '.' are blanks.

        Any other characters (spaces, newlines, '|', '-', '+') are ignored so
        that both one-line strings and pretty-printed boards are accepted.
        """
        # Keep only cell symbols so borders and newlines in a printed board are ignored.
        symbols = [ch for ch in text if ch.isdigit() or ch == "."]
        if len(symbols) != 81:
            raise ValueError(f"expected 81 cells, found {len(symbols)}")
        # zip pairs the 81 symbols with the 81 cells in the same row-major order.
        values = {
            cell: (0 if ch == "." else int(ch)) for cell, ch in zip(CELLS, symbols)
        }
        return cls(values)

    def copy(self) -> "Grid":
        # dict(...) copies the mapping so later edits do not change the original.
        return Grid(dict(self.values))

    def __getitem__(self, cell: Cell) -> int:
        return self.values[cell]

    def __setitem__(self, cell: Cell, digit: int) -> None:
        self.values[cell] = digit

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Grid) and self.values == other.values

    def givens(self) -> list[tuple[Cell, int]]:
        """Cells that already have a digit. 0 is falsy, so empty cells drop out."""
        return [(cell, d) for cell, d in self.values.items() if d]

    def empty_cells(self) -> list[Cell]:
        return [cell for cell, d in self.values.items() if not d]

    def is_complete(self) -> bool:
        """True when the assignment is a total function from cells to digits."""
        return all(self.values.values())

    def conflicts(self) -> list[tuple[Unit, int]]:
        """Every (unit, digit) pair where the digit appears more than once."""
        found = []
        for unit in UNITS:
            digits = [self.values[cell] for cell in unit.cells if self.values[cell]]
            # set(digits) drops duplicates so each repeated digit is reported once.
            for d in set(digits):
                if digits.count(d) > 1:
                    found.append((unit, d))
        return found

    def is_solved(self) -> bool:
        """A solution is a complete grid whose restriction to every unit is 1-to-1."""
        return self.is_complete() and not self.conflicts()

    def to_string(self) -> str:
        return "".join(str(self.values[cell]) if self.values[cell] else "." for cell in CELLS)

    def pretty(self) -> str:
        lines = []
        for r in ROWS:
            # Draw a line before rows 4 and 7 so the three bands of boxes show up.
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
