"""Sudoku solved with discrete mathematics: sets, logic, and proofs.

Importing sudoku_logic exposes the pieces a script usually needs:
the Grid type, the CNF encoding, and the three solvers.
"""

from .backtracking import count_solutions, solve_backtracking
from .board import Grid
from .deduction import solve_logically
from .logic import encode, sudoku_rules
from .sat import solve_sat

__all__ = [
    "Grid",
    "count_solutions",
    "encode",
    "solve_backtracking",
    "solve_logically",
    "solve_sat",
    "sudoku_rules",
]
