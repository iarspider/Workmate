import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field

from tabulate import tabulate

reports = {}


def report(_func=None, *, name=None):
    def decorator(func):
        key = name or func.__name__
        reports[key] = func
        return func

    if _func is None:
        return decorator
    return decorator(_func)


def parse_args():
    parser = argparse.ArgumentParser(prog="Workmate")
    parser.add_argument("--files", help="Файлы для обработки", nargs="+", required=True)
    parser.add_argument(
        "--report",
        help="Имя отчёта для формирования",
        choices=reports.keys(),
        required=True,
    )
    return parser.parse_args()


def load_files(files):
    rows = []
    for path in files:
        # Robust CSV handling
        with open(path, "r", newline="", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)
            rows.extend(reader)
    return rows


@report(name="average-rating")
def average_rating(data: list[dict[str, str]]):
    @dataclass
    class Rating:
        rating_sum: float = field(default=0.0)
        count: int = field(default=0)

        def __iadd__(self, other):
            # Accept int/float; assume input valid overall
            self.rating_sum += float(other)
            self.count += 1
            return self

        @property
        def value(self) -> float:
            return self.rating_sum / self.count

    acc: defaultdict[str, Rating] = defaultdict(Rating)
    for entry in data:
        acc[entry["brand"]] += entry["rating"]  # coerced in __iadd__

    # Produce sorted rows directly, no defaultdict rewrap
    items = sorted(acc.items(), key=lambda kv: kv[1].value, reverse=True)
    result = [
        {"": i, "brand": brand, "rating": round(r.value, 2)}
        for i, (brand, r) in enumerate(items, 1)
    ]
    return result


def print_report(rows, report_file=None):
    if report_file is None:
        report_file = sys.stdout
    print(tabulate(rows, headers="keys", tablefmt="psql"), file=report_file)


def main():
    args = parse_args()
    data = load_files(args.files)
    rows = reports[args.report](data)
    print_report(rows)


if __name__ == "__main__":  # pragma: no cover
    main()
