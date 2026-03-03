"""
Course Schedule Conflict Checker

Detects scheduling conflicts for students enrolled in multiple courses.
A conflict occurs when a student has two or more courses that overlap in time
on the same day.

CSV Input Format:
    student_id, course_code, course_name, days, start_time, end_time

    - days: one or more day codes separated by commas, e.g. "M,W,F" or "T,Th"
            Accepted codes: M, T, W, Th, F (Mon–Fri)
    - start_time / end_time: 24-hour format (HH:MM) or 12-hour format (H:MM AM/PM)

Usage:
    python conflict_checker.py schedule.csv
    python conflict_checker.py schedule.csv --output conflicts.csv
"""

import csv
import sys
import argparse
from datetime import datetime
from collections import defaultdict
from itertools import combinations


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DAY_CODES = {"M", "T", "W", "Th", "F"}


def parse_time(value: str) -> datetime:
    """Parse a time string in HH:MM (24-hr) or H:MM AM/PM (12-hr) format."""
    value = value.strip()
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognised time format: '{value}'. Use HH:MM or H:MM AM/PM.")


def parse_days(value: str) -> list[str]:
    """Parse a comma-separated string of day codes, e.g. 'M,W,F' -> ['M','W','F']."""
    days = [d.strip() for d in value.split(",") if d.strip()]
    invalid = [d for d in days if d not in DAY_CODES]
    if invalid:
        raise ValueError(
            f"Unknown day code(s): {invalid}. Accepted codes: {sorted(DAY_CODES)}"
        )
    return days


def times_overlap(start_a: datetime, end_a: datetime,
                  start_b: datetime, end_b: datetime) -> bool:
    """Return True if time range A and time range B overlap (exclusive on end)."""
    return start_a < end_b and end_a > start_b


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {"student_id", "course_code", "course_name", "days", "start_time", "end_time"}


def load_schedule(path: str) -> list[dict]:
    """Read the CSV and return a list of course-enrolment dicts."""
    enrolments = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file appears to be empty.")
        actual = {c.strip().lower() for c in reader.fieldnames}
        missing = REQUIRED_COLUMNS - actual
        if missing:
            raise ValueError(f"CSV is missing required column(s): {missing}")

        for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
            # Normalise column names (strip whitespace, lowercase)
            row = {k.strip().lower(): v.strip() for k, v in row.items()}
            try:
                enrolments.append({
                    "student_id": row["student_id"],
                    "course_code": row["course_code"],
                    "course_name": row["course_name"],
                    "days": parse_days(row["days"]),
                    "start_time": parse_time(row["start_time"]),
                    "end_time": parse_time(row["end_time"]),
                    "_raw_start": row["start_time"],
                    "_raw_end": row["end_time"],
                })
            except ValueError as exc:
                print(f"  Warning – skipping row {i}: {exc}", file=sys.stderr)

    return enrolments


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def find_conflicts(enrolments: list[dict]) -> list[dict]:
    """Return a list of conflict records for every overlapping course pair."""
    # Group enrolments by student
    by_student: dict[str, list[dict]] = defaultdict(list)
    for e in enrolments:
        by_student[e["student_id"]].append(e)

    conflicts = []
    for student_id, courses in by_student.items():
        # Check every pair of courses for that student
        for a, b in combinations(courses, 2):
            # Find days they share
            shared_days = set(a["days"]) & set(b["days"])
            for day in shared_days:
                if times_overlap(a["start_time"], a["end_time"],
                                 b["start_time"], b["end_time"]):
                    conflicts.append({
                        "student_id": student_id,
                        "day": day,
                        "course_a_code": a["course_code"],
                        "course_a_name": a["course_name"],
                        "course_a_time": f"{a['_raw_start']} – {a['_raw_end']}",
                        "course_b_code": b["course_code"],
                        "course_b_name": b["course_name"],
                        "course_b_time": f"{b['_raw_start']} – {b['_raw_end']}",
                    })
    return conflicts


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_conflicts(conflicts: list[dict]) -> None:
    if not conflicts:
        print("No conflicts found.")
        return

    print(f"\nFound {len(conflicts)} conflict(s):\n")
    for c in conflicts:
        print(
            f"  Student {c['student_id']}  |  {c['day']}\n"
            f"    {c['course_a_code']} ({c['course_a_name']})  {c['course_a_time']}\n"
            f"    {c['course_b_code']} ({c['course_b_name']})  {c['course_b_time']}\n"
        )


def write_conflicts_csv(conflicts: list[dict], path: str) -> None:
    fieldnames = [
        "student_id", "day",
        "course_a_code", "course_a_name", "course_a_time",
        "course_b_code", "course_b_name", "course_b_time",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(conflicts)
    print(f"Conflicts written to: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find student course schedule conflicts from a CSV file."
    )
    parser.add_argument("schedule", help="Path to the schedule CSV file")
    parser.add_argument(
        "--output", "-o",
        metavar="FILE",
        help="Optional path to write conflicts to a CSV file",
    )
    args = parser.parse_args()

    try:
        enrolments = load_schedule(args.schedule)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading schedule: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(enrolments)} enrolment(s) from '{args.schedule}'.")

    conflicts = find_conflicts(enrolments)
    print_conflicts(conflicts)

    if args.output:
        write_conflicts_csv(conflicts, args.output)


if __name__ == "__main__":
    main()
