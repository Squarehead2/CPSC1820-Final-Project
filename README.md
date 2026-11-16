# Sudoku Solver Using Logic

CPSC 1820 Discrete Structures final project, by William Black, Darrel Nguyen, and Lam Dao.

This project models Sudoku as a problem in discrete mathematics. It writes the rules in
predicate and propositional logic, solves puzzles step by step with named rules of
inference, and compares that human-style reasoning with systematic methods
(backtracking search and a SAT solver).

## Running it

You need Python 3.10 or newer ([python.org/downloads](https://www.python.org/downloads/)).
There are no other dependencies.

```
python main.py list                         # sample puzzles
python main.py rules                        # rules in predicate logic + clause counting
python main.py encode easy                  # puzzle as a CNF formula
python main.py encode easy --dimacs easy.cnf  # export for any SAT solver
python main.py explain easy                 # step-by-step proof (first 40 steps)
python main.py explain contradiction --limit 0   # all steps
python main.py solve inkala --method sat    # methods: logic, backtrack, sat
python main.py compare                      # every method on every puzzle
python -m unittest -v                       # run the tests
```

A puzzle can be a library name (`easy`, `medium`, `pairs`, `contradiction`, `hard`,
`inkala`), a text file, or an 81-character string using `.` or `0` for blanks.

## Project layout

| File | What it does |
| --- | --- |
| `sudoku_logic/board.py` | The board as sets: cells, units, and the peer relation |
| `sudoku_logic/logic.py` | Propositions P(r,c,n), the rules in CNF, model checking, counting |
| `sudoku_logic/deduction.py` | Human-style solving, where every step is a rule of inference |
| `sudoku_logic/backtracking.py` | Recursive search, plus a uniqueness proof by exhaustion |
| `sudoku_logic/sat.py` | DPLL SAT solver that only sees the clauses |
| `sudoku_logic/compare.py` | Runs every method on a puzzle and measures its work |
| `sudoku_logic/puzzles.py` | Sample puzzles from easy to extremely hard |
| `main.py` | Command-line interface |
| `tests/test_sudoku.py` | Unit tests |

## The discrete math, concept by concept

### Sets, functions, and relations (`board.py`)

- Rows, columns, and digits all come from the set D = {1, ..., 9}. The cells are the
  Cartesian product D × D, so there are 81 of them.
- A *unit* is a row, column, or 3×3 box. There are 27 units, and each is a 9-element
  subset of D × D.
- Two cells are *peers* if they share a unit. "Is a peer of" is a relation that is
  **symmetric** and **irreflexive**, and every cell has exactly 20 peers. The tests check
  these properties.
- A solved grid is a function f : D × D → D whose restriction to each unit is a
  bijection.

### Predicate logic (`python main.py rules`)

Let P(r, c, n) mean "the cell in row r, column c holds digit n". Then the rules are:

| Rule | Predicate logic |
| --- | --- |
| Each cell holds a digit | ∀r ∀c ∃n P(r,c,n) |
| Each cell holds at most one digit | ∀r ∀c ∀n ∀m (n ≠ m → ¬(P(r,c,n) ∧ P(r,c,m))) |
| Each row contains every digit | ∀r ∀n ∃c P(r,c,n) |
| No row repeats a digit | ∀r ∀n ∀c ∀c' (c ≠ c' → ¬(P(r,c,n) ∧ P(r,c',n))) |

Columns and boxes follow the same pattern.

### Propositional logic and CNF (`logic.py`)

Every variable ranges over a finite domain, so the quantifiers can be expanded:
∃ becomes a disjunction (∨) and ∀ becomes a conjunction (∧). Each P(r,c,n) becomes one
of 9³ = 729 Boolean variables. By De Morgan's law, ¬(a ∧ b) ≡ ¬a ∨ ¬b, so every rule
becomes a set of clauses, and the whole puzzle is one formula in Conjunctive Normal Form.

The map `var(r, c, n) = 81(r−1) + 9(c−1) + n` is a bijection from {1..9}³ to
{1..729}. It gives each proposition a number in the standard DIMACS format.

### Counting

| Clause group | Counting argument | Clauses |
| --- | --- | --- |
| Cell has at least one digit | 81 cells | 81 |
| Cell has at most one digit | 81 · C(9,2) | 2,916 |
| Unit contains every digit | 27 units · 9 digits | 243 |
| Unit has no repeats | 27 · 9 · C(9,2) | 8,748 |
| **Total** | | **11,988** |

There are 2^729 ≈ 10^219 truth assignments, and 9^81 ≈ 10^77 ways to write digits in
the grid. That is why trying everything is hopeless and deduction matters.

### Rules of inference (`deduction.py`, `python main.py explain`)

Each cell has a candidate set: the digits n for which ¬P(r,c,n) has not yet been
proved. Every solving step proves a new P or ¬P and records why.

| Technique | Inference rule |
| --- | --- |
| Elimination after placing a digit | **Modus ponens**: P(r,c,n) → ¬P(x,n) for every peer x |
| Naked single | **Disjunctive syllogism** on the cell clause P(r,c,1) ∨ … ∨ P(r,c,9) |
| Hidden single | **Disjunctive syllogism** on a unit clause "some cell in this row holds n" |
| Locked candidates | One unit's "contains n" clause can only be satisfied inside a second unit |
| Naked pair | **Proof by cases**: two cells limited to {a, b} must use up both a and b |
| Contradiction | **Proof by contradiction**: assume P(r,c,n), derive ⊥, conclude ¬P(r,c,n) |

### Proofs about the solvers

- **Model checking.** `solve` converts the answer back to a truth assignment and checks
  that all of the roughly 12,000 clauses are true.
- **Proof by exhaustion.** `count_solutions` searches the whole tree. Finding exactly
  one solution proves that the solution is unique.
- **Induction and recursion.** Backtracking is correct by induction on the number of
  empty cells: each recursive call has one fewer empty cell, and a full grid is the
  base case.

## Human reasoning vs. systematic solving

Results from `python main.py compare` (times vary by computer):

| Puzzle | Deduction | Backtracking, reading order | Backtracking, most constrained cell | DPLL SAT |
| --- | --- | --- | --- | --- |
| easy | solved, singles only | 4,209 nodes | 52 nodes | 0 guesses |
| pairs | solved, needs naked pairs | 85,258 nodes | 353 nodes | 2 guesses |
| contradiction | needs 1 proof by contradiction | 16,880 nodes | 1,396 nodes | 1 guess |
| hard | solved, needs locked candidates | gave up at 200,000 | 719 nodes | 15 guesses |
| inkala | **stuck, no progress** | 49,559 nodes | 13,811 nodes | 89 guesses |

Some observations for the report:

- On easy puzzles, DPLL's **unit propagation** finishes with zero guesses. Unit
  propagation is the clause version of naked and hidden singles, so a computer doing
  pure propositional logic reaches the same conclusions a person does.
- Picking the **most constrained cell** (the fewest candidates) is what people do
  instinctively. It cuts the search tree by a factor of 10 to 1,000.
- Inkala's "world's hardest" puzzle defeats every direct technique here, including
  one level of proof by contradiction. Only nested case analysis (search) finishes it.
  That marks a clear boundary between "logic a person can follow" and "systematic
  search".

## References

- Rosen, K. H. (2019). *Discrete Mathematics and Its Applications* (8th ed.). McGraw-Hill Education.
- Norvig, P. (n.d.). [Solving Every Sudoku Puzzle](https://www.norvig.com/sudoku.html).
- CodeLucky. (2026, January 13). *Sudoku solver algorithm: Backtracking explained for beginners* [Video]. YouTube.
