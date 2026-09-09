"""Boundary and uncertainty checks for the maintained academic calendars."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from academic_week import (  # noqa: E402
    assessment_anchors, describe_date, describe_range, load_calendar, main, semester_anchors,
)


class AcademicWeekTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar = load_calendar()

    def test_anchors_name_each_short_semester(self):
        self.assertEqual(
            semester_anchors(self.calendar, "2025-2026", "秋冬学期"),
            "本学年秋一周周一：2025 年 9 月 15 日；本学年冬一周周一：2025 年 11 月 10 日",
        )
        self.assertEqual(semester_anchors(self.calendar, "2025-2026", "夏"), "本学年夏一周周一：2026 年 4 月 27 日")

    def test_assessment_anchors_select_only_the_dates_short_term(self):
        autumn = "本学年秋一周周一：2025 年 9 月 15 日"
        self.assertEqual(assessment_anchors(self.calendar, "2025-2026", "2025-10-13"), autumn)
        self.assertEqual(assessment_anchors(self.calendar, "2025-2026", "2025-09-15", "2025-09-28"), autumn)
        self.assertEqual(assessment_anchors(self.calendar, "2025-2026", "2025-10-13", "2025-10-13"), autumn)
        self.assertEqual(
            assessment_anchors(self.calendar, "2025-2026", "2026-04-30", "2026-05-06"),
            "本学年夏一周周一：2026 年 4 月 27 日",
        )

    def test_assessment_anchors_include_both_terms_at_boundary(self):
        self.assertEqual(
            assessment_anchors(self.calendar, "2025-2026", "2026-04-26", "2026-04-27"),
            "本学年春一周周一：2026 年 3 月 2 日；本学年夏一周周一：2026 年 4 月 27 日",
        )
        self.assertEqual(
            assessment_anchors(self.calendar, "2025-2026", "2025-11-09", "2025-11-10"),
            "本学年秋一周周一：2025 年 9 月 15 日；本学年冬一周周一：2025 年 11 月 10 日",
        )

    def test_assessment_anchors_cross_vacation_and_include_intermediate_terms(self):
        self.assertEqual(
            assessment_anchors(self.calendar, "2025-2026", "2026-01-16", "2026-03-02"),
            "本学年冬一周周一：2025 年 11 月 10 日；本学年春一周周一：2026 年 3 月 2 日",
        )
        self.assertEqual(
            assessment_anchors(self.calendar, "2025-2026", "2025-10-13", "2026-04-27"),
            "本学年秋一周周一：2025 年 9 月 15 日；本学年冬一周周一：2025 年 11 月 10 日；"
            "本学年春一周周一：2026 年 3 月 2 日；本学年夏一周周一：2026 年 4 月 27 日",
        )

    def test_assessment_anchors_reject_invalid_or_unverified_endpoints(self):
        for start, end in (("2025-9-15", None), ("2025-09-15", "2025-9-28"),
                           ("2026-04-27", "2026-04-26"), ("2026-01-17", "2026-03-02"),
                           ("2026-01-16", "2026-01-17"), ("2026-02-28", None)):
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                assessment_anchors(self.calendar, "2025-2026", start, end)
        with self.assertRaisesRegex(ValueError, "缺少校历"):
            assessment_anchors(self.calendar, "2021-2022", "2021-10-01")
        calendar = deepcopy(self.calendar)
        calendar["years"]["2025-2026"]["terms"]["冬"]["break_start"] = None
        calendar["years"]["2025-2026"]["terms"]["冬"]["exam_week_start"] = None
        with self.assertRaisesRegex(ValueError, "缺少假期起点.*无法核对"):
            assessment_anchors(calendar, "2025-2026", "2026-01-05")
        self.assertEqual(
            assessment_anchors(self.calendar, "2019-2020", "2020-02-24"),
            "本学年春一周周一：2020 年 2 月 24 日（原校历计划，实际教学安排未核对）",
        )

    def test_sunday_to_monday_increments_week(self):
        self.assertEqual(describe_date(self.calendar, "2025-2026", "2025-09-15"), "秋第 1 周周一")
        self.assertEqual(describe_date(self.calendar, "2025-2026", "2025-10-12"), "秋第 4 周周日")
        self.assertEqual(describe_date(self.calendar, "2025-2026", "2025-10-13"), "秋第 5 周周一")
        self.assertEqual(
            describe_range(self.calendar, "2025-2026", "2025-10-11", "2025-10-13"),
            "秋第 4 周周六—秋第 5 周周一",
        )

    def test_spring_summer_boundary_resets_week(self):
        self.assertEqual(
            describe_range(self.calendar, "2025-2026", "2026-04-26", "2026-04-27"),
            "春第 8 周周日—夏第 1 周周一",
        )

    def test_all_seven_neuroscience_opening_ranges(self):
        cases = [
            ("2026-03-19", "2026-03-25", "春第 3 周周四—春第 4 周周三"),
            ("2026-04-02", "2026-04-08", "春第 5 周周四—春第 6 周周三"),
            ("2026-04-16", "2026-04-22", "春第 7 周周四—春第 8 周周三"),
            ("2026-04-30", "2026-05-06", "夏第 1 周周四—夏第 2 周周三"),
            ("2026-05-14", "2026-05-20", "夏第 3 周周四—夏第 4 周周三"),
            ("2026-05-28", "2026-06-03", "夏第 5 周周四—夏第 6 周周三"),
            ("2026-06-18", "2026-06-24", "夏第 8 周周四—夏考试周周三"),
        ]
        for start, end, expected in cases:
            with self.subTest(start=start, end=end):
                self.assertEqual(describe_range(self.calendar, "2025-2026", start, end), expected)

    def test_winter_examination_period_is_not_week_nine(self):
        self.assertEqual(describe_date(self.calendar, "2025-2026", "2026-01-08"), "冬考试周周四")

    def test_calendar_year_boundary_does_not_reset_winter_week(self):
        self.assertEqual(
            describe_range(self.calendar, "2025-2026", "2025-12-29", "2026-01-04"),
            "冬第 8 周周一—冬第 8 周周日",
        )

    def test_holidays_and_outside_dates_are_rejected(self):
        for day in ("2025-09-14", "2026-01-17", "2026-02-28", "2026-07-05", "2026-09-09"):
            with self.subTest(day=day), self.assertRaisesRegex(ValueError, "范围之外或寒暑假"):
                describe_date(self.calendar, "2025-2026", day)
        with self.assertRaises(ValueError):
            describe_range(self.calendar, "2025-2026", "2026-01-16", "2026-01-17")

    def test_missing_calendar_never_borrows_another_year(self):
        for year in ("2021-2022", "2018-2019"):
            with self.subTest(year=year):
                self.assertIsNone(semester_anchors(self.calendar, year, "秋冬"))
                with self.assertRaisesRegex(ValueError, "缺少校历"):
                    describe_date(self.calendar, year, f"{year[:4]}-10-01")

    def test_historical_numbered_tenth_week_is_not_truncated(self):
        self.assertEqual(describe_date(self.calendar, "2020-2021", "2020-11-16"), "秋第 10 周周一")
        self.assertEqual(describe_date(self.calendar, "2020-2021", "2020-11-23"), "冬第 1 周周一")
        self.assertEqual(describe_date(self.calendar, "2020-2021", "2021-01-28"), "冬第 10 周周四")

    def test_unverified_2020_plan_has_explicit_notice(self):
        self.assertEqual(
            describe_date(self.calendar, "2019-2020", "2020-02-24"),
            "春第 1 周周一（原校历计划，实际教学安排未核对）",
        )
        self.assertIn("实际教学安排未核对", semester_anchors(self.calendar, "2019-2020", "春夏"))
        self.assertIn("实际教学安排未核对", describe_date(self.calendar, "2019-2020", "2020-04-27"))
        self.assertNotIn("未核对", describe_date(self.calendar, "2019-2020", "2019-09-09"))

    def test_unknown_break_boundary_cannot_extend_past_eight_weeks(self):
        for term, safe_day, uncertain_day in (("冬", "2026-01-04", "2026-01-05"), ("夏", "2026-06-21", "2026-06-22")):
            with self.subTest(term=term):
                calendar = deepcopy(self.calendar)
                calendar["years"]["2025-2026"]["terms"][term]["break_start"] = None
                calendar["years"]["2025-2026"]["terms"][term]["exam_week_start"] = None
                self.assertIn("第 8 周", describe_date(calendar, "2025-2026", safe_day))
                with self.assertRaisesRegex(ValueError, "缺少假期起点.*无法核对"):
                    describe_date(calendar, "2025-2026", uncertain_day)
                calendar["years"]["2025-2026"]["terms"][term]["numbered_weeks"] = None
                with self.assertRaisesRegex(ValueError, "无法核对"):
                    describe_date(calendar, "2025-2026", uncertain_day)

    def test_extended_autumn_is_natural_week_not_examination_week(self):
        calendar = deepcopy(self.calendar)
        calendar["years"]["2020-2021"]["terms"]["秋"]["numbered_weeks"] = 8
        self.assertEqual(describe_date(calendar, "2020-2021", "2020-11-16"), "秋起第 10 个自然周周一")

    def test_missing_numbered_weeks_use_natural_weeks(self):
        calendar = deepcopy(self.calendar)
        calendar["years"]["2020-2021"]["terms"]["秋"]["numbered_weeks"] = None
        self.assertEqual(describe_date(calendar, "2020-2021", "2020-11-16"), "秋起第 10 个自然周周一")

    def test_no_examination_period_is_inferred_without_source_field(self):
        calendar = deepcopy(self.calendar)
        calendar["years"]["2025-2026"]["terms"]["夏"]["exam_week_start"] = None
        self.assertEqual(describe_date(calendar, "2025-2026", "2026-06-24"), "夏起第 9 个自然周周三")
        calendar["years"]["2025-2026"]["terms"]["夏"]["exam_week_start"] = "2026-06-25"
        self.assertEqual(describe_date(calendar, "2025-2026", "2026-06-24"), "夏起第 9 个自然周周三")
        self.assertEqual(describe_date(calendar, "2025-2026", "2026-06-25"), "夏考试周周四")

    def test_strict_iso_dates_and_range_order(self):
        for value in ("2025-2-03", "2025.10.13", "2025-02-29", "2026-13-01", "2026-04-31", "2025-10-13T08:00:00", "2025-10-13 ", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                describe_date(self.calendar, "2025-2026", value)
        with self.assertRaisesRegex(ValueError, "结束日期不能早于"):
            describe_range(self.calendar, "2025-2026", "2025-10-13", "2025-10-12")
        self.assertEqual(describe_range(self.calendar, "2025-2026", "2025-10-13", "2025-10-13"), "秋第 5 周周一")

    def test_invalid_year_and_semester_are_rejected(self):
        for year in ("2025", "2025-2027", "2025-2024", "0000-0001", 2025):
            with self.subTest(year=year), self.assertRaises(ValueError):
                semester_anchors(self.calendar, year, "秋")
        with self.assertRaises(ValueError):
            semester_anchors(self.calendar, "2025-2026", "秋春")

    def test_invalid_calendar_values_are_rejected(self):
        mutations = [
            ("week1_monday", "2025-09-16"),
            ("week1_monday", "2024-09-16"),
            ("week1_monday", "2025-12-01"),
            ("numbered_weeks", 0),
            ("numbered_weeks", 54),
            ("numbered_weeks", True),
            ("numbered_weeks", "8"),
            ("numbered_weeks", 8.0),
            ("status", "assumed"),
            ("break_start", "2025-11-11"),
        ]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                calendar = deepcopy(self.calendar)
                calendar["years"]["2025-2026"]["terms"]["秋"][key] = value
                with self.assertRaises(ValueError):
                    describe_date(calendar, "2025-2026", "2025-10-13")
        calendar = deepcopy(self.calendar)
        calendar["years"]["2025-2026"]["terms"]["冬"]["break_start"] = "2026-03-03"
        with self.assertRaisesRegex(ValueError, "寒假起点"):
            describe_date(calendar, "2025-2026", "2025-10-13")

    def test_load_validates_schema_years_and_partial_terms(self):
        invalid = [
            {"schema_version": True, "years": {}},
            {"schema_version": 2, "years": {}},
            {"schema_version": 1, "years": []},
            {"schema_version": 1, "years": {"2025-2027": {"terms": {}}}},
            {"schema_version": 1, "years": {"2025-2026": {"terms": {"秋": {}}}}},
        ]
        for calendar in invalid:
            with self.subTest(calendar=calendar), patch.object(Path, "open", return_value=io.StringIO(json.dumps(calendar))):
                with self.assertRaises(ValueError):
                    load_calendar("unused.json")
        with patch.object(Path, "open", return_value=io.StringIO("{broken")):
            with self.assertRaisesRegex(ValueError, "JSON 格式错误"):
                load_calendar("unused.json")

    def test_cli_json_and_error_exit(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main(["--year", "2025-2026", "--date", "2026-06-18", "--end", "2026-06-24", "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(errors.getvalue(), "")
        self.assertEqual(json.loads(output.getvalue()), {
            "year": "2025-2026", "start": "2026-06-18", "end": "2026-06-24",
            "description": "夏第 8 周周四—夏考试周周三",
        })
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            status = main(["--year", "2021-2022", "--date", "2022-01-12"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("缺少校历", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
