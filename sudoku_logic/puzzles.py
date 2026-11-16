"""Sample puzzles, from easy to very hard. '.' marks an empty cell."""

PUZZLES: dict[str, tuple[str, str]] = {
    "easy": (
        "Wikipedia's example puzzle. Singles alone solve it.",
        "53..7...."
        "6..195..."
        ".98....6."
        "8...6...3"
        "4..8.3..1"
        "7...2...6"
        ".6....28."
        "...419..5"
        "....8..79",
    ),
    "medium": (
        "Peter Norvig's first example grid.",
        "..3.2.6.."
        "9..3.5..1"
        "..18.64.."
        "..81.29.."
        "7.......8"
        "..67.82.."
        "..26.95.."
        "8..2.3..9"
        "..5.1.3..",
    ),
    "pairs": (
        "Needs naked pairs (proof by cases) and locked candidates.",
        "..46.8..."
        ".721....."
        ".9.....6."
        ".....1..."
        "4.6.5...1"
        "7...2.8.."
        "9..5.7.8."
        ".8...963."
        "......1..",
    ),
    "contradiction": (
        "Direct rules get stuck; one proof by contradiction unlocks it.",
        "....53..."
        "...6..1.5"
        "6..49...."
        "...2.7..6"
        "3.98...2."
        "2.....5.4"
        ".2.9...68"
        ".38...9.."
        ".........",
    ),
    "hard": (
        "Peter Norvig's second example. Only 17 clues; needs locked candidates.",
        "4.....8.5"
        ".3......."
        "...7....."
        ".2.....6."
        "....8.4.."
        "....1...."
        "...6.3.7."
        "5..2....."
        "1.4......",
    ),
    "inkala": (
        "Arto Inkala's 2012 'world's hardest Sudoku'.",
        "8........"
        "..36....."
        ".7..9.2.."
        ".5...7..."
        "....457.."
        "...1...3."
        "..1....68"
        "..85...1."
        ".9....4..",
    ),
}
