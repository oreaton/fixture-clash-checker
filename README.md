# clashcheck

A command-line tool that checks a sports fixture list for scheduling clashes:
two matches booked at the same venue with overlapping kick-off windows, or
the same team listed to play two matches at once.

Grassroots leagues tend to build their fixture list by hand in a spreadsheet
once a season, and it's easy for a pitch to get double-booked or for a
club's first and reserve teams to end up sharing a slot without anyone
noticing until match day. clashcheck reads the list and reports every clash
it finds so it can be fixed before publishing.

## Usage

```
python clashcheck.py fixtures.csv
python clashcheck.py fixtures.csv --buffer 30
python clashcheck.py fixtures.csv --format json
```

`--buffer MINUTES` requires at least that many minutes between fixtures at
the same venue or involving the same team, not just non-overlapping times.
Use it to account for pitch turnaround, or for the time it takes a team to
travel between venues.

`--format json` prints a single JSON object to stdout instead of the
line-by-line text report, for use in CI pipelines that want to gate a build
on clashes:

```
{
  "clash_count": 1,
  "clashes": [
    {
      "kind": "venue",
      "detail": "both at 'Elm Park'",
      "a": {"line": 2, "start": "2026-09-22T14:00:00", "end": "2026-09-22T15:30:00", "venue": "Elm Park", "home": "Reds", "away": "Blues"},
      "b": {"line": 3, "start": "2026-09-22T15:00:00", "end": "2026-09-22T16:30:00", "venue": "Elm Park", "home": "Whites", "away": "Greens"}
    }
  ]
}
```

With `--format json`, a file that can't be read is reported as a JSON object
on stderr (`{"error": "..."}`) rather than plain text, so scripts only have
to parse one format.

Exit status is 0 if no clashes were found, 1 if clashes were found, and 2 if
the input file couldn't be read.

## Fixture file format

A CSV with a header row: `date,time,duration,venue,home,away`

- `date` — `YYYY-MM-DD`
- `time` — 24-hour `HH:MM`, local pitch time
- `duration` — match length in minutes (include warm-up time if you want
  that covered too)
- `venue`, `home`, `away` — free text

Example `fixtures.csv`:

```
date,time,duration,venue,home,away
2026-09-22,14:00,90,Elm Park,Reds,Blues
2026-09-22,15:30,90,Elm Park,Whites,Greens
2026-09-22,14:30,90,Oak Field,Reds,Greens
```

Running `python clashcheck.py fixtures.csv --buffer 30` on this file reports
two clashes: Elm Park is booked back-to-back with no turnaround, and Reds are
listed to play two overlapping matches at different venues on the same
afternoon.

## Tests

```
python -m unittest discover tests
```

The test suite is table-driven: each case is a fixture list, a buffer
setting, and the clash kinds it should produce, covering the edges that are
easy to get wrong — fixtures that only just touch, venue names that differ
by case or spacing, and a fixture that runs past midnight.
