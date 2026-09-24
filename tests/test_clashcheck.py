import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import clashcheck  # noqa: E402


def fixture(line, start, duration_minutes, venue, home, away):
    start_dt = datetime.strptime(start, "%Y-%m-%d %H:%M")
    end_dt = start_dt + clashcheck.timedelta(minutes=duration_minutes)
    return clashcheck.Fixture(line, start_dt, end_dt, venue, home, away)


# Each case: (name, fixtures, buffer_minutes, expected clash kinds, unordered)
CASES = [
    (
        "back-to-back same venue, no buffer required -> no clash",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 15:30", 90, "Elm Park", "Whites", "Greens"),
        ],
        0,
        [],
    ),
    (
        "back-to-back same venue, 30min turnaround required -> venue clash",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 15:30", 90, "Elm Park", "Whites", "Greens"),
        ],
        30,
        ["venue"],
    ),
    (
        "same team double-booked at two different venues -> team clash",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 14:30", 90, "Oak Field", "Reds", "Greens"),
        ],
        0,
        ["team"],
    ),
    (
        "venue name differs only in case and spacing -> still the same venue",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 14:30", 90, "  elm   park", "Whites", "Greens"),
        ],
        0,
        ["venue"],
    ),
    (
        "fixture crossing midnight still clashes with an early match next day",
        [
            fixture(2, "2026-09-22 23:30", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-23 00:30", 60, "Elm Park", "Whites", "Greens"),
        ],
        0,
        ["venue"],
    ),
    (
        "identical fixture listed twice -> both a venue and a team clash",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
        ],
        0,
        ["venue", "team"],
    ),
    (
        "same venue and same teams but different days -> no clash",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-23 14:00", 90, "Elm Park", "Reds", "Blues"),
        ],
        0,
        [],
    ),
    (
        "three-way overlap counts each pair separately",
        [
            fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues"),
            fixture(3, "2026-09-22 14:30", 90, "Elm Park", "Whites", "Greens"),
            fixture(4, "2026-09-22 15:00", 90, "Elm Park", "Grays", "Blacks"),
        ],
        0,
        ["venue", "venue", "venue"],
    ),
]


class FindClashesTest(unittest.TestCase):
    def test_cases(self):
        for name, fixtures, buffer_minutes, expected_kinds in CASES:
            with self.subTest(name=name):
                clashes = clashcheck.find_clashes(fixtures, buffer_minutes)
                self.assertEqual(sorted(c.kind for c in clashes), sorted(expected_kinds))


class ParseRowTest(unittest.TestCase):
    def test_parses_a_valid_row(self):
        row = {
            "date": "2026-09-22",
            "time": "14:00",
            "duration": "90",
            "venue": "Elm Park",
            "home": "Reds",
            "away": "Blues",
        }
        parsed = clashcheck.parse_row(2, row)
        self.assertEqual(parsed.start, datetime(2026, 9, 22, 14, 0))
        self.assertEqual(parsed.end, datetime(2026, 9, 22, 15, 30))

    def test_team_cannot_play_itself(self):
        row = {
            "date": "2026-09-22",
            "time": "14:00",
            "duration": "90",
            "venue": "Elm Park",
            "home": "Reds",
            "away": "reds",
        }
        with self.assertRaises(ValueError):
            clashcheck.parse_row(2, row)

    def test_blank_team_name_is_rejected(self):
        row = {
            "date": "2026-09-22",
            "time": "14:00",
            "duration": "90",
            "venue": "Elm Park",
            "home": "Reds",
            "away": "   ",
        }
        with self.assertRaises(ValueError):
            clashcheck.parse_row(2, row)

    def test_missing_column_is_rejected(self):
        row = {
            "date": "2026-09-22",
            "time": "14:00",
            "duration": "90",
            "venue": "Elm Park",
            "home": "Reds",
        }
        with self.assertRaises(ValueError):
            clashcheck.parse_row(2, row)


class BuildReportTest(unittest.TestCase):
    def test_empty_clash_list(self):
        report = clashcheck.build_report([])
        self.assertEqual(report, {"clash_count": 0, "clashes": []})

    def test_serializes_a_clash(self):
        a = fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues")
        b = fixture(3, "2026-09-22 14:30", 90, "Elm Park", "Whites", "Greens")
        clashes = clashcheck.find_clashes([a, b])
        report = clashcheck.build_report(clashes)

        self.assertEqual(report["clash_count"], 1)
        entry = report["clashes"][0]
        self.assertEqual(entry["kind"], "venue")
        self.assertEqual(entry["a"]["line"], 2)
        self.assertEqual(entry["a"]["start"], "2026-09-22T14:00:00")
        self.assertEqual(entry["a"]["venue"], "Elm Park")
        self.assertEqual(entry["b"]["line"], 3)

    def test_report_is_json_serializable(self):
        a = fixture(2, "2026-09-22 14:00", 90, "Elm Park", "Reds", "Blues")
        b = fixture(3, "2026-09-22 14:30", 90, "Elm Park", "Reds", "Greens")
        clashes = clashcheck.find_clashes([a, b])
        report = clashcheck.build_report(clashes)
        # round-trips without error and preserves the clash count
        decoded = clashcheck.json.loads(clashcheck.json.dumps(report))
        self.assertEqual(decoded["clash_count"], 2)


if __name__ == "__main__":
    unittest.main()
