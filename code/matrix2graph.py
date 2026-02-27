from __future__ import annotations

import argparse
import re
import sys
from decimal import Decimal
from fractions import Fraction
from numbers import Number
from typing import Any, TextIO, cast

VAL_PATTERN = re.compile(r"[-]?(\d+/\d+)|[-]?(\d+(\.\d+)?)")


def parse_val(x: str) -> Number:
    x = x.strip()
    assert VAL_PATTERN.fullmatch(x) is not None, x
    if "/" in x:
        return cast(Number, Fraction(x))
    elif "." in x:
        return cast(Number, Decimal(x))
    else:
        return cast(Number, int(x))


type Entry = Number | list[Entry]


def parse_list(text: str) -> list[Entry]:
    text = text.strip()
    if not text:
        raise ValueError("Input is blank/empty")
    if not text.startswith("{"):
        raise ValueError(f"Unexpected start char: {text[0]!r}")
    if not text.endswith("}"):
        raise ValueError(f"Unexpected end char: {text[-1]!r}")
    text = text[1:-1]  # remove leading/trailing
    index = 0
    result = []
    while index < len(text):
        c = text[index]
        # ignoring comma is sorta bad since it means we don't reject invalid input
        if c.isspace() or c == ",":
            index += 1
            continue
        elif c == "{":
            # NOTE: Only handles one level of nesting
            end_index = text.index("}", index)
            result.append(parse_list(text[index : end_index + 1]))
            index = end_index + 1
        elif (c.isdigit() or c == '-') and (m := VAL_PATTERN.match(text, index)) is not None:
            result.append(parse_val(m.group(0)))
            index = m.end() + 1
        else:
            raise ValueError(
                f"Unexpected value starting at {index}, {text[index : index + 10]!r}"
            )
    return result


class Matrix:
    rows: int
    columns: int
    _entries: list[list[Number]]

    def __init__(self, rows: int, columns: int, entries: list[list[Number]]):
        self.rows = rows
        self.columns = columns
        assert rows > 0
        assert columns > 0
        # defensive copy
        self._entries = entries = [list(row) for row in entries]
        if len(entries) != rows:
            raise ValueError(f"Expected {rows} rows, but got {len(entries)}")
        for row, row_values in enumerate(entries):
            if len(row_values) != columns:
                raise ValueError(
                    f"Expected {columns} columns for row {row}, but got {len(row_values)}"
                )
            for value in row_values:
                assert isinstance(value, Number), (row, column, value)

    def __getitem__(self, index: tuple[int, int]) -> Number:
        match index:
            case (int(row), int(col)):
                return self._entries[row][col]
            case _:
                raise TypeError(index)

    def __str__(self):
        def print_col(col: list[Number]) -> str:
            return "{" + ",".join(list(map(str, col))) + "}"

        return "{" + ",".join(map(print_col, self._entries)) + "}"

    @classmethod
    def parse(cls, text: str) -> Matrix:
        raw_entries = parse_list(text)
        num_rows = len(raw_entries)
        if num_rows == 0:
            raise ValueError("Cannot have zero rows")
        num_columns = None
        entries: list[None | list[Number]] = [None] * num_rows
        for row, column_entries in enumerate(raw_entries):
            if not isinstance(column_entries, list):
                raise ValueError(
                    f"Row at index {row} should have a list of column entries"
                )
            if num_columns is None:
                num_columns = len(column_entries)
            if len(column_entries) != num_columns:
                raise ValueError(
                    f"Row at index {row} has {len(column_entries)} entries, not {num_columns}"
                )
            current_row = entries[row] = [None] * num_columns
            for column, entry in enumerate(column_entries):
                if not isinstance(entry, Number):
                    raise ValueError(
                        f"Entry at {row},{column} should be a number, not {type(entry)}"
                    )
                assert entry is not None
                current_row[column] = entry
        assert num_columns is not None
        return Matrix(num_rows, num_columns, cast(list[list[Number]], entries))

    def verify_stochastic(self) -> None:
        """
        Verify this is a stochastic matrix, with all rows summing to one.

        This is the convention used in the books by Hoel/Port/Stone and Lawler.
        """
        if self.rows != self.columns:
            raise ValueError(
                f"A stochastic matrix should be square, not {self.rows}x{self.columns}"
            )
        for row in range(self.rows):
            row_sum = 0
            for col in range(self.columns):
                row_sum += cast(Any, self[row, col])
            if row_sum != 1:
                raise ValueError(
                    f"Expected row at index {row} to sum to 1, but got {row_sum!r}"
                )


def to_dotfile(m: Matrix, *, vertex_start_index: int = 0) -> str:
    def serialize_vertex(x: int) -> str:
        return str(x + vertex_start_index)
    lines: list[str] = []
    for row in range(m.rows):
        for col in range(m.columns):
            weight = m[row, col]
            if weight == 0:
                continue
            lines.append(f'{serialize_vertex(row)} -> {serialize_vertex(col)} [label="{weight}"];')
    return "\n".join(["digraph {", *["  " + line for line in lines], "}"])


def _open_maybe_stdin(file_name: str) -> TextIO:
    if file_name == "-":
        return sys.stdin
    else:
        return open(file_name, "rt")


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("infile")
    parser.add_argument("--non-stochastic", action="store_true")
    parser.add_argument("--vertex-start-index", default=0, type=int)
    args = parser.parse_args(args)
    with _open_maybe_stdin(args.infile) as f:
        matrix = Matrix.parse(f.read())
    if not args.non_stochastic:
        matrix.verify_stochastic()
    print(to_dotfile(matrix, vertex_start_index=args.vertex_start_index))


if __name__ == "__main__":
    main(sys.argv[1:])
