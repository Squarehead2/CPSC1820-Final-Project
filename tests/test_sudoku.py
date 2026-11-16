import unittest

from sudoku_logic.backtracking import count_solutions, solve_backtracking
from sudoku_logic.board import CELLS, PEERS, UNITS, Grid
from sudoku_logic.deduction import Contradiction, solve_logically
from sudoku_logic.logic import (
    NUM_VARS,
    encode,
    evaluate,
    grid_to_assignment,
    sudoku_rules,
    unvar,
    var,
)
from sudoku_logic.puzzles import PUZZLES
from sudoku_logic.sat import solve_sat

EASY = Grid.parse(PUZZLES["easy"][1])
EASY_SOLUTION = Grid.parse(
    "534678912672195348198342567859761423426853791"
    "713924856961537284287419635345286179"
)


class BoardTests(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(len(CELLS), 81)
        self.assertEqual(len(UNITS), 27)
        self.assertTrue(all(len(u.cells) == 9 for u in UNITS))

    def test_peer_relation_is_symmetric_and_irreflexive(self):
        for cell in CELLS:
            self.assertEqual(len(PEERS[cell]), 20)
            self.assertNotIn(cell, PEERS[cell])
            for peer in PEERS[cell]:
                self.assertIn(cell, PEERS[peer])

    def test_parse_round_trip(self):
        self.assertEqual(Grid.parse(EASY.pretty()), EASY)
        self.assertEqual(Grid.parse(EASY.to_string()), EASY)


class LogicTests(unittest.TestCase):
    def test_var_is_a_bijection(self):
        seen = {var(r, c, n) for r in range(1, 10) for c in range(1, 10) for n in range(1, 10)}
        self.assertEqual(seen, set(range(1, NUM_VARS + 1)))
        for v in range(1, NUM_VARS + 1):
            self.assertEqual(var(*unvar(v)), v)

    def test_clause_counts(self):
        counts = {name: len(cl) for name, cl in sudoku_rules().groups.items()}
        self.assertEqual(list(counts.values()), [81, 2916, 243, 8748])
        self.assertEqual(len(sudoku_rules()), 11988)

    def test_solution_satisfies_every_clause(self):
        self.assertEqual(evaluate(encode(EASY), grid_to_assignment(EASY_SOLUTION)), [])

    def test_wrong_grid_violates_clauses(self):
        broken = EASY_SOLUTION.copy()
        broken[(1, 1)], broken[(1, 2)] = broken[(1, 2)], broken[(1, 1)]
        self.assertTrue(evaluate(encode(EASY), grid_to_assignment(broken)))


class SolverTests(unittest.TestCase):
    def test_every_method_solves_easy(self):
        self.assertEqual(solve_logically(EASY).grid, EASY_SOLUTION)
        self.assertEqual(solve_backtracking(EASY).solution, EASY_SOLUTION)
        self.assertEqual(solve_sat(EASY).grid(), EASY_SOLUTION)

    def test_all_puzzles_unique_and_methods_agree(self):
        for name, (_, text) in PUZZLES.items():
            with self.subTest(puzzle=name):
                grid = Grid.parse(text)
                self.assertEqual(count_solutions(grid).solutions_found, 1)
                sat = solve_sat(grid).grid()
                self.assertTrue(sat.is_solved())
                self.assertEqual(solve_backtracking(grid).solution, sat)
                logic = solve_logically(grid)
                for cell, n in logic.grid.givens():
                    self.assertEqual(sat[cell], n, "deduction must never place a wrong digit")

    def test_deduction_steps_are_justified(self):
        result = solve_logically(EASY)
        self.assertTrue(result.solved)
        self.assertTrue(all(step.formal for step in result.steps))
        placed = sum(1 for step in result.steps if step.placement)
        self.assertEqual(placed, len(EASY.empty_cells()))

    def test_invalid_clues_are_rejected(self):
        bad = EASY.copy()
        bad[(1, 3)] = 5  # R1C1 is already 5
        with self.assertRaises(Contradiction):
            solve_logically(bad)
        self.assertFalse(solve_sat(bad).satisfiable)


if __name__ == "__main__":
    unittest.main()
