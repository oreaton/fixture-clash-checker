"""Find venue and team scheduling clashes in a sports fixture list.

Reads a CSV of fixtures and reports any pair that:
  - shares a venue with overlapping (or too-close) kick-off windows, or
  - shares a team that would need to play two matches at once.
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta

FIELDS = ("date", "time", "duration", "venue", "home", "away")


@dataclass
class Fixture:
    line: int
    start: datetime
    end: datetime
    venue: str
    home: str
    away: str

    @property
    def venue_key(self) -> str:
        return " ".join(self.venue.split()).lower()

    def team_key(self, name: str) -> str:
        return " ".join(name.split()).lower()

    def teams(self) -> set:
        return {self.team_key(self.home), self.team_key(self.away)}


@dataclass
class Clash:
    kind: str  # "venue" or "team"
    detail: str
    a: Fixture
    b: Fixture

    def __str__(self) -> str:
        return f"{self.kind.upper()} CLASH: line {self.a.line} and line {self.b.line} ({self.detail})"


def parse_row(line_no: int, row: dict) -> Fixture:
    for field in FIELDS:
        if field not in row or row[field] is None:
            raise ValueError(f"line {line_no}: missing column {field!r}")

    date = row["date"].strip()
    time = row["time"].strip()
    try:
        start = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError(f"line {line_no}: bad date/time {date!r} {time!r}: {exc}") from exc

    try:
        duration = int(row["duration"].strip())
    except ValueError as exc:
        raise ValueError(f"line {line_no}: bad duration {row['duration']!r}") from exc

    venue = row["venue"].strip()
    home = row["home"].strip()
    away = row["away"].strip()
    if not venue or not home or not away:
        raise ValueError(f"line {line_no}: venue, home and away cannot be blank")
    if home.lower() == away.lower():
        raise ValueError(f"line {line_no}: {home!r} cannot play itself")

    return Fixture(line_no, start, start + timedelta(minutes=duration), venue, home, away)


def load_fixtures(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [parse_row(line_no, row) for line_no, row in enumerate(reader, start=2)]


def overlaps(a: Fixture, b: Fixture, buffer_minutes: int) -> bool:
    # Fixtures that merely touch (a.end == b.start) are not a clash unless a
    # buffer is required between them, so the gap is compared as strictly-less.
    gap = timedelta(minutes=buffer_minutes)
    return a.start < b.end + gap and b.start < a.end + gap


def find_clashes(fixtures: list, buffer_minutes: int = 0) -> list:
    clashes = []
    for i in range(len(fixtures)):
        for j in range(i + 1, len(fixtures)):
            a, b = fixtures[i], fixtures[j]
            if not overlaps(a, b, buffer_minutes):
                continue
            if a.venue_key == b.venue_key:
                clashes.append(Clash("venue", f"both at {a.venue!r}", a, b))
            shared_teams = a.teams() & b.teams()
            if shared_teams:
                names = ", ".join(sorted(shared_teams))
                clashes.append(Clash("team", f"{names} scheduled twice", a, b))
    return clashes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Find venue and team scheduling clashes in a sports fixture CSV."
    )
    parser.add_argument("csv_path", help="path to a fixtures CSV file")
    parser.add_argument(
        "--buffer",
        type=int,
        default=0,
        metavar="MINUTES",
        help="minimum gap required between fixtures at the same venue or for the same team",
    )
    args = parser.parse_args(argv)

    try:
        fixtures = load_fixtures(args.csv_path)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    clashes = find_clashes(fixtures, args.buffer)
    if not clashes:
        print("no clashes found")
        return 0

    for clash in clashes:
        print(clash)
    return 1


if __name__ == "__main__":
    sys.exit(main())
