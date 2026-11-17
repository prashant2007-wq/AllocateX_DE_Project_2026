# Phase 2: Baseline Timings (Team T0037)

## Environment

- **PostgreSQL**: 14.20 (Homebrew)
- **Hardware**: MacBook, Apple M4, macOS 27.2
- **Method**: `EXPLAIN (ANALYZE, BUFFERS)`, 3 runs per query, all three `Execution Time` values recorded from `benchmarks/results/baseline/`. Average = arithmetic mean of runs 1, 2, 3.
- **Indexes at time of benchmark**: Only PRIMARY KEY and UNIQUE indexes — no additional indexes (untuned baseline).
- **Write queries W01–W05**: each run was wrapped in `BEGIN; EXPLAIN (ANALYZE, BUFFERS) ...; ROLLBACK;` by the benchmark script. Row count of `lesson_attempts` verified at 188,300 before and after.

---

## Timing Table

| SQL Query | Type | Run 1 (ms) | Run 2 (ms) | Run 3 (ms) | Average (ms) |
|---|---|---|---|---|---|
| R01: Course path — units and lessons of Spanish course in order | READ | 0.198 | 0.221 | 0.411 | 0.277 |
| R02: Home screen — learner 1042 courses with total XP | READ | 0.091 | 0.143 | 0.156 | 0.130 |
| R03: Streak counter — learner 1042 current streak to 30 Jun 2026 | READ | 0.408 | 0.160 | 0.387 | 0.318 |
| R04: Daily goal ring — XP learner 1042 earned on 30 Jun 2026 | READ | 17.583 | 12.783 | 10.691 | 13.686 |
| R05: Leagues tab — cohort leaderboard for week of 29 Jun 2026 | READ | 4.291 | 2.932 | 3.196 | 3.473 |
| R06: Start button — first uncompleted lesson for learner 1042 | READ | 21.449 | 15.707 | 14.380 | 17.179 |
| R07: Curriculum — lessons with most mistakes per attempt (100+ attempts) | READ | 35.479 | 33.995 | 33.416 | 34.297 |
| R08: Analytics — quit rate per lesson type | READ | 33.790 | 33.567 | 35.582 | 34.313 |
| R09: Growth — daily active learners in June 2026 | READ | 13.287 | 13.876 | 13.208 | 13.457 |
| R10: Monetisation — streak freezes per subscription tier in 2026 | READ | 12.649 | 12.901 | 12.288 | 12.613 |
| R11: Sign-in by username | READ | 0.058 | 0.063 | 0.053 | 0.058 |
| R12: Profile — learner 1042 achievements, newest first | READ | 0.137 | 0.140 | 0.274 | 0.184 |
| R13: Referral programme — learners who have not referred anyone | READ | 20.805 | 12.431 | 12.692 | 15.309 |
| R14: Leagues — promotion/demotion rates per tier, last 4 weeks | READ | 6.662 | 5.878 | 6.253 | 6.264 |
| R15: Retention — learners who joined Jan 2026 and active in Jun 2026 | READ | 6.110 | 6.298 | 4.673 | 5.694 |
| R16: Friends — search learners by username starting with "Karan" | READ | 12.532 | 10.215 | 8.707 | 10.485 |
| R17: Analytics — perfect-lesson rate per device in 2026 | READ | 36.831 | 29.499 | 29.011 | 31.780 |
| R18: Course popularity — enrollments per course, new in 2026 | READ | 11.304 | 11.234 | 11.332 | 11.290 |
| R19: Curriculum report — completions and avg mistakes per lesson (Spanish) | READ | 3663.399 | 3647.016 | 3633.280 | 3647.898 |
| R20: Growth — XP per day and running total, June 2026 | READ | 15.066 | 15.386 | 15.234 | 15.229 |
| R21: Streak reminders — active 23–29 Jun but not on 30 Jun | READ | 4.915 | 4.965 | 4.662 | 4.847 |
| R22: Support console — lesson attempts newest first, page 4001 | READ | 69.501 | 72.079 | 72.712 | 71.431 |
| R23: Monetisation — paid learners in India active last 7 days Jun 2026 | READ | 14.517 | 14.482 | 14.540 | 14.513 |
| R24: Curriculum — avg hearts lost per lesson by CEFR level | READ | 46.516 | 46.404 | 46.376 | 46.432 |
| R25: Notifications — lessons started per hour per country | READ | 228.120 | 236.861 | 226.034 | 230.338 |
| W01: Lesson start — learner 1042 starts lesson 1 | WRITE | 0.958 | 0.937 | 0.891 | 0.929 |
| W02: Lesson end — finish most recent unfinished attempt of 30 Jun | WRITE | 1.056 | 1.179 | 1.153 | 1.129 |
| W03: Daily activity — add 20 XP to learner 1042 on 1 Jul 2026 | WRITE | 1.672 | 1.606 | 1.921 | 1.733 |
| W04: Weekly league close — rank everyone and set promotion results | WRITE | 20.115 | 14.679 | 12.183 | 15.659 |
| W05: Achievements catch-up — award XP_100 badge to qualifying learners | WRITE | 77.031 | 74.206 | 75.781 | 75.673 |
| **Total (sum of all 30 averages)** | | | | | **4278.888** |

---

## Scan Type and Explanation per Query

| Query | Scan type(s) in plan | Why it is slow or fast |
|---|---|---|
| R01 | Seq Scan on units, Seq Scan on courses, Index Scan using uq_lesson_no | Fast: small tables (11 courses, 220 units); index scan on lessons for the join; total rows tiny |
| R02 | Index Scan using enrollments_pkey, Seq Scan on courses | Fast: PK lookup on (learner_id, course_id) is instant; courses table has only 11 rows |
| R03 | Index Only Scan using daily_activity_pkey | Fast: PK leads with learner_id so the index covers the WHERE learner_id=1042 filter; CTE is small |
| R04 | Index Scan using learners_pkey, Seq Scan on lesson_attempts | Slow: learner lookup is fast via PK, but no index on lesson_attempts.learner_id, so 188k rows are scanned to find one learner's attempts |
| R05 | Index Scan using league_memberships_pkey, Seq Scan on league_memberships, Index Scan using learners_pkey | Moderate: subquery uses PK to get cohort_id; outer join still scans full league_memberships because PK leads with learner_id not week_start |
| R06 | Index Scan using uq_unit_no, Index Scan using uq_lesson_no, Seq Scan on lesson_attempts | Slow: index scans find the lessons quickly, but NOT EXISTS forces a full Seq Scan of 188k lesson_attempts for each lesson candidate |
| R07 | Seq Scan on lesson_attempts, Seq Scan on lessons, Seq Scan on units | Slow: no index on lesson_attempts.lesson_id or units.course_id; must scan all 188k attempts, join 1760 lessons and 220 units |
| R08 | Seq Scan on lesson_attempts, Seq Scan on lessons | Slow: full table scan of 188k lesson_attempts to compute quit rate; join to lessons (1760 rows) also sequential |
| R09 | Seq Scan on daily_activity | Slow: 189k rows in daily_activity scanned to filter a date range; no index on activity_date |
| R10 | Seq Scan on daily_activity, Index Scan using learners_pkey | Moderate: daily_activity scanned fully for year filter; learners joined via PK (fast), but EXTRACT(YEAR …) on activity_date is not sargable |
| R11 | Index Scan using learners_username_key | Fast: UNIQUE index on username gives an instant single-row lookup — the fastest query in the set |
| R12 | Index Scan using learner_achievements_pkey, Seq Scan on achievements | Fast: PK on (learner_id, achievement_id) covers the learner filter; achievements has only 10 rows |
| R13 | Seq Scan on learners | Slow and returns 0 rows: NOT IN with a subquery that includes NULLs (referred_by is NULL for most learners) causes every row to evaluate to UNKNOWN — see correctness note below |
| R14 | Seq Scan on league_memberships | Moderate: filters four weeks of league data; no index on week_start, so 28k rows scanned |
| R15 | Seq Scan on learners, Index Scan using daily_activity_pkey | Moderate: learners scanned for Jan 2026 join date; daily_activity lookup uses PK (learner_id prefix), but correlated EXISTS runs per matching learner |
| R16 | Index Scan using learners_username_key | Moderate: ILIKE 'karan%' with a leading literal can use a B-tree index scan on username; still reads a range of the index to find all matches |
| R17 | Seq Scan on lesson_attempts | Slow: 188k rows scanned to filter completed and EXTRACT(YEAR …)=2026; no index on started_at or completed_at |
| R18 | Seq Scan on enrollments, Seq Scan on courses | Moderate: both tables must be fully scanned for the GROUP BY; enrollments has 37.5k rows and courses only 11 |
| R19 | Index Scan using uq_unit_no, Index Scan using uq_lesson_no, Seq Scan on lesson_attempts | **Slowest (3647 ms)**: 160 lessons in the Spanish course, each with two correlated subqueries; each subquery does a full Seq Scan of 188k lesson_attempts — 320 sequential scans total |
| R20 | Seq Scan on lesson_attempts | Slow: cast started_at::date filters June; no index on started_at, so all 188k rows read; window function then runs over result |
| R21 | Index Only Scan using daily_activity_pkey | Fast: PK on (learner_id, activity_date) covers both the date range filter and the NOT EXISTS check; only reads the index, not the heap |
| R22 | Seq Scan on lesson_attempts | Slow: sort 188k rows by started_at DESC, then discard 100,000 (OFFSET); no index on started_at means full scan plus a large sort |
| R23 | Seq Scan on daily_activity, Seq Scan on learners | Moderate: both tables scanned; filters on country_code and subscription are not indexed; date filter on daily_activity not sargable |
| R24 | Seq Scan on lesson_attempts, Seq Scan on lessons, Seq Scan on units | Slow: three full table scans to aggregate hearts_lost across all 188k attempts, joined to 1760 lessons and 220 units |
| R25 | Seq Scan on lesson_attempts, Seq Scan on learners | Slow: all 188k attempts joined to 30k learners to group by country and hour; no index on learner_id in lesson_attempts |
| W01 | (no scan) | Fast: single-row INSERT into lesson_attempts with a known PK; no scan needed, just a PK constraint check |
| W02 | Index Scan using lesson_attempts_pkey | Fast: PK scan to find max(attempt_id) matching the filter; single-row UPDATE by PK |
| W03 | (no scan) | Fast: single-row UPSERT on (learner_id, activity_date) PK; no scan |
| W04 | Seq Scan on league_memberships | Moderate: must scan all 28.6k rows of the week to compute row_number() per cohort; no index on week_start |
| W05 | Seq Scan on achievements, Seq Scan on enrollments | Slow for a write: Seq Scan on enrollments (37.5k rows) to aggregate XP; Seq Scan on achievements (10 rows) for XP_100 lookup; inserts ~4000 rows with conflict check |

---

## Result-Correctness Note

**R13 returns 0 rows.** The query is:
```sql
SELECT l.learner_id, l.username
FROM learners l
WHERE l.learner_id NOT IN (SELECT r.referred_by FROM learners r);
```
`learners.referred_by` is `NULL` for the majority of learners (most have no referrer recorded). When a subquery used with `NOT IN` contains even one `NULL`, SQL three-valued logic means the predicate evaluates to `UNKNOWN` for every row in the outer query — so no row ever passes. This is a known SQL NULL-propagation trap, **not a data problem**.

The correct fix is `NOT EXISTS` with a correlated subquery or adding `WHERE r.referred_by IS NOT NULL` inside the subquery. This fix belongs to **CP3** (the optimised query file); the original query is left unchanged here because the baseline must reflect the unmodified workload.
