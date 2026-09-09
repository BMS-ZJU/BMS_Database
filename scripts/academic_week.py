"""Calculate assessment dates against the project's verified academic calendars.

The module uses only Python's standard library. It does not infer examination
dates or treat calendar plans as confirmation of actual teaching arrangements.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys
from typing import Any

DEFAULT_CALENDAR = Path(__file__).resolve().parents[1] / "ACADEMIC_CALENDAR.json"
TERMS = ("秋", "冬", "春", "夏")
SEMESTERS = {"秋": ("秋",), "冬": ("冬",), "春": ("春",), "夏": ("夏",),
             "秋冬": ("秋", "冬"), "春夏": ("春", "夏")}
WEEKDAYS = "一二三四五六日"
PLANNED_NOTICE = "原校历计划，实际教学安排未核对"


def _parse_year(year: str) -> tuple[int, int]:
    if not isinstance(year, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{4}", year):
        raise ValueError("学年必须使用 YYYY-YYYY 格式")
    first, second = map(int, year.split("-"))
    if not 1 <= first < second <= 9999 or second != first + 1:
        raise ValueError(f"学年年份必须相邻：{year}")
    return first, second


def _parse_date(value: str, field: str = "日期") -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError(f"{field}必须使用 YYYY-MM-DD 格式")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}不是有效日期：{value}") from exc


def _validate_calendar(calendar: dict[str, Any]) -> None:
    if not isinstance(calendar, dict) or type(calendar.get("schema_version")) is not int or calendar["schema_version"] != 1:
        raise ValueError("校历 schema_version 必须为 1")
    years = calendar.get("years")
    if not isinstance(years, dict):
        raise ValueError("校历 years 必须为学年对象")
    for year, entry in years.items():
        first, second = _parse_year(year)
        if not isinstance(entry, dict) or not isinstance(entry.get("terms"), dict):
            raise ValueError(f"{year} 的 terms 必须为对象")
        terms = entry["terms"]
        if not terms:  # An explicit missing-calendar record is valid.
            continue
        if set(terms) != set(TERMS):
            raise ValueError(f"{year} 必须完整记录秋冬春夏四学期，或使用空 terms 标记校历缺失")
        starts = {}
        breaks = {}
        for term in TERMS:
            info = terms[term]
            label = f"{year} {term}学期"
            required = {"week1_monday", "numbered_weeks", "break_start", "status"}
            if not isinstance(info, dict) or not required.issubset(info):
                raise ValueError(f"{label} 缺少必要校历字段")
            start = _parse_date(info["week1_monday"], f"{label}起点")
            if start.weekday() != 0:
                raise ValueError(f"{label} week1_monday 必须为周一")
            expected_year = first if term in ("秋", "冬") else second
            if start.year != expected_year:
                raise ValueError(f"{label}起点年份应为 {expected_year}")
            numbered = info["numbered_weeks"]
            if numbered is not None and (type(numbered) is not int or not 1 <= numbered <= 53):
                raise ValueError(f"{label} numbered_weeks 必须为 1 至 53 的整数或 null")
            if info["status"] not in ("calendar", "planned_actual_unverified"):
                raise ValueError(f"{label} status 无法识别")
            starts[term] = start
            break_value = info["break_start"]
            if term in ("秋", "春") and break_value is not None:
                raise ValueError(f"{label}使用下一学期起点作为结束边界，break_start 应为 null")
            if break_value is not None:
                break_day = _parse_date(break_value, f"{label}假期起点")
                if break_day <= start or break_day.year not in (start.year, second):
                    raise ValueError(f"{label}假期起点必须晚于学期起点且位于对应学年")
                if term == "夏" and break_day.year != second:
                    raise ValueError(f"{label}暑假起点年份应为 {second}")
                breaks[term] = break_day
        if not all(starts[left] < starts[right] for left, right in zip(TERMS, TERMS[1:])):
            raise ValueError(f"{year} 秋冬春夏起点顺序错误")
        if "冬" in breaks and breaks["冬"] > starts["春"]:
            raise ValueError(f"{year} 寒假起点不能晚于春学期起点")
        for term in TERMS:
            info = terms[term]
            numbered = info["numbered_weeks"]
            end = starts["冬"] if term == "秋" else starts["夏"] if term == "春" else breaks.get(term)
            if numbered is not None and end is not None and (end - starts[term]).days <= 7 * (numbered - 1):
                raise ValueError(f"{year} {term}学期结束边界未覆盖最后一个编号周")
            exam_value = info.get("exam_week_start")
            if exam_value is not None:
                if term not in ("冬", "夏") or term not in breaks or numbered is None:
                    raise ValueError(f"{year} {term}学期独立考试周须有冬夏编号周范围及假期起点")
                exam_start = _parse_date(exam_value, f"{year} {term}学期考试周起点")
                if exam_start.weekday() != 0:
                    raise ValueError(f"{year} {term}学期考试周起点必须为周一")
                if (exam_start - starts[term]).days < 7 * numbered or exam_start >= breaks[term]:
                    raise ValueError(f"{year} {term}学期独立考试周应位于编号周之后、假期之前")


def load_calendar(path: str | Path = DEFAULT_CALENDAR) -> dict[str, Any]:
    """Load and validate the maintained calendar; never fetch remote data."""
    try:
        with Path(path).open(encoding="utf-8-sig") as stream:
            calendar = json.load(stream)
    except json.JSONDecodeError as exc:
        raise ValueError(f"校历 JSON 格式错误：{exc.msg}") from exc
    _validate_calendar(calendar)
    return calendar


def _year_terms(calendar: dict[str, Any], year: str) -> dict[str, Any] | None:
    _parse_year(year)
    _validate_calendar(calendar)
    entry = calendar["years"].get(year)
    return entry["terms"] if entry and entry["terms"] else None


def _notice(info: dict[str, Any]) -> str:
    return f"（{PLANNED_NOTICE}）" if info["status"] == "planned_actual_unverified" else ""


def _format_anchors(terms: dict[str, Any], selected: tuple[str, ...]) -> str:
    anchors = []
    for term in selected:
        info = terms[term]
        start = _parse_date(info["week1_monday"])
        anchors.append(f"本学年{term}一周周一：{start.year} 年 {start.month} 月 {start.day} 日{_notice(info)}")
    return "；".join(anchors)


def semester_anchors(calendar: dict[str, Any], year: str, semester: str) -> str | None:
    """Return the requested short-semester anchors, or None if unavailable."""
    if not isinstance(semester, str):
        raise ValueError("学期必须为秋、冬、春、夏、秋冬或春夏")
    semester = semester.removesuffix("学期")
    if semester not in SEMESTERS:
        raise ValueError("学期必须为秋、冬、春、夏、秋冬或春夏")
    terms = _year_terms(calendar, year)
    if terms is None:
        return None
    return _format_anchors(terms, SEMESTERS[semester])


def _term_bounds(terms: dict[str, Any]) -> dict[str, tuple[date, date]]:
    starts = {term: _parse_date(info["week1_monday"]) for term, info in terms.items()}
    bounds = {}
    for term in TERMS:
        info = terms[term]
        start = starts[term]
        if term in ("秋", "春"):
            end = starts["冬" if term == "秋" else "夏"]
        elif info["break_start"] is not None:
            end = _parse_date(info["break_start"])
        else:
            end = start + timedelta(weeks=8)
        bounds[term] = (start, end)
    return bounds


def _term_for_date(terms: dict[str, Any], year: str, day: date) -> str:
    bounds = _term_bounds(terms)
    for term, (start, end) in bounds.items():
        if start <= day < end:
            return term
    for term in ("冬", "夏"):
        if terms[term]["break_start"] is None:
            upper = bounds["春"][0] if term == "冬" else date(_parse_year(year)[1], 12, 31)
            if bounds[term][1] <= day < upper:
                raise ValueError(f"{year} {term}学期缺少假期起点，日期 {day.isoformat()} 已超过 8 个自然周，无法核对")
    raise ValueError(f"日期 {day.isoformat()} 位于 {year} 已核对校历范围之外或寒暑假，不能计算周次")


def assessment_anchors(calendar: dict[str, Any], year: str, start: str, end: str | None = None) -> str:
    """Return anchors for the short terms touched by a confirmed date or range.

    Both endpoints must lie in verified term periods, as for describe_range.
    Interior vacations add no term; every intervening short term is included.
    This date-based selection does not change the course's recorded semester.
    """
    first = _parse_date(start, "开始日期")
    last = first if end is None else _parse_date(end, "结束日期")
    if first > last:
        raise ValueError("结束日期不能早于开始日期")
    terms = _year_terms(calendar, year)
    if terms is None:
        raise ValueError(f"{year} 学年缺少校历，无法确认学期起点")
    _term_for_date(terms, year, first)
    _term_for_date(terms, year, last)
    selected = tuple(term for term, (left, right) in _term_bounds(terms).items()
                     if left <= last and first < right)
    return _format_anchors(terms, selected)


def _describe(terms: dict[str, Any], year: str, day: date) -> str:
    term = _term_for_date(terms, year, day)
    info = terms[term]
    start = _parse_date(info["week1_monday"])
    week = (day - start).days // 7 + 1
    weekday = f"周{WEEKDAYS[day.weekday()]}"
    if info["numbered_weeks"] is None:
        label = f"{term}起第 {week} 个自然周{weekday}"
    elif week <= info["numbered_weeks"]:
        label = f"{term}第 {week} 周{weekday}"
    elif info.get("exam_week_start") is not None and day >= _parse_date(info["exam_week_start"]):
        label = f"{term}考试周{weekday}"
    else:
        label = f"{term}起第 {week} 个自然周{weekday}"
    return label + _notice(info)


def describe_date(calendar: dict[str, Any], year: str, date_iso: str) -> str:
    """Describe an explicit date without inferring the actual assessment date."""
    day = _parse_date(date_iso)
    terms = _year_terms(calendar, year)
    if terms is None:
        raise ValueError(f"{year} 学年缺少校历，无法计算周次")
    return _describe(terms, year, day)


def describe_range(calendar: dict[str, Any], year: str, start: str, end: str) -> str:
    """Describe both endpoints of an explicit opening period."""
    first, last = _parse_date(start, "开始日期"), _parse_date(end, "结束日期")
    if first > last:
        raise ValueError("结束日期不能早于开始日期")
    terms = _year_terms(calendar, year)
    if terms is None:
        raise ValueError(f"{year} 学年缺少校历，无法计算周次")
    left = _describe(terms, year, first)
    return left if first == last else f"{left}—{_describe(terms, year, last)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="根据本地校历核对学期起点并计算日期周次")
    parser.add_argument("--calendar", type=Path, default=DEFAULT_CALENDAR, help="校历 JSON，默认使用仓库根目录文件")
    parser.add_argument("--year", required=True, help="学年，例如 2025-2026")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--date", help="日期 YYYY-MM-DD；配合 --end 可计算区间")
    mode.add_argument("--term", help="秋、冬、春、夏、秋冬或春夏")
    parser.add_argument("--end", help="区间结束日期 YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)
    if args.end and not args.date:
        parser.error("--end 必须与 --date 一起使用")
    try:
        calendar = load_calendar(args.calendar)
        result: dict[str, Any] = {"year": args.year}
        if args.term:
            value = semester_anchors(calendar, args.year, args.term)
            if value is None:
                raise ValueError(f"{args.year} 学年缺少校历，无法确认学期起点")
            result.update(term=args.term, anchors=value)
        elif args.end:
            value = describe_range(calendar, args.year, args.date, args.end)
            result.update(start=args.date, end=args.end, description=value)
        else:
            value = describe_date(calendar, args.year, args.date)
            result.update(date=args.date, description=value)
    except (ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False) if args.json else value)
    return 0


if __name__ == "__main__":
    # Stable Unicode output for Windows shells and JSON consumers.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
