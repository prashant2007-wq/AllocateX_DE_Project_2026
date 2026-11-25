# Phase 3: Optimization Report (Team T0037)

## 1. Method and Environment

- **PostgreSQL**: psql (PostgreSQL) 14.20 (Homebrew)
- **Hardware**: MacBook, Apple M4, macOS 27.2
- **Baseline**: 3 runs per query (`benchmarks/run_benchmark.sh duolingo_dbms baseline`), average of Execution Time.
- **Optimized**: 5 runs per query (`benchmarks/run_benchmark.sh duolingo_dbms optimized 5 sql/06_optimized_queries.sql`), average of Execution Time.
- **Indexes before baseline**: only PK / UNIQUE indexes (untuned).
- **Write queries W01–W05**: each run inside `BEGIN; EXPLAIN (ANALYZE, BUFFERS) …; ROLLBACK;` — data unchanged.
- All numbers below are read directly from `benchmarks/results/baseline/summary.csv` and `benchmarks/results/optimized/summary.csv`.

## 2. Optimization Table

| Query | Before (ms) | Problem found in the plan | Optimization applied | After (ms) | Improvement | Same result? |
|---|---|---|---|---|---|---|
| R01 | 0.277 | Small tables (11 courses, 220 units); sequential scan is fast enough | Unchanged — already fast with existing small tables and index scan on lessons | 0.371 | -33.9% | Yes |
| R02 | 0.130 | PK scan on enrollments(learner_id,course_id) covers the lookup instantly | Unchanged — PK lookup is already optimal | 0.112 | +13.8% | Yes |
| R03 | 0.318 | PK on (learner_id, activity_date) allows an Index Only Scan on the small result | Unchanged — Index Only Scan on PK already covers the query | 0.179 | +43.7% | Yes |
| R04 | 13.686 | DATE() function wrapper on started_at blocks any index; full Seq Scan of 188k attempts | Replaced DATE(started_at)='2026-06-30' with range predicate; idx_attempts_learner_started used | 0.199 | +98.5% | Yes |
| R05 | 3.473 | PK leads with learner_id; week_start filter forces a Seq Scan of 28k league rows | Added idx_league_week_cohort(week_start,cohort_id) INCLUDE; Index Only Scan on league | 0.470 | +86.5% | Yes |
| R06 | 17.179 | NOT EXISTS probe scans full 188k lesson_attempts for each uncompleted lesson | Added idx_attempts_learner_lesson_done partial index; NOT EXISTS probe uses Index Only Scan | 0.485 | +97.2% | Yes |
| R07 | 34.297 | No index on lesson_attempts.lesson_id; Seq Scan over 188k rows for group-by | Added idx_attempts_lesson_cover(lesson_id) INCLUDE; Index Only Scan replaces Seq Scan | 15.505 | +54.8% | Yes |
| R08 | 34.313 | Must read all 188k attempts to compute quit rate; no meaningful filter to push | Unchanged — quit_pct requires reading all attempts; no selective filter exists | 35.919 | -4.7% | Yes |
| R09 | 13.457 | No index on daily_activity.activity_date; Seq Scan of 189k rows for June filter | Added idx_daily_date_cover(activity_date) INCLUDE(learner_id,xp); Index Only Scan | 2.280 | +83.1% | Yes |
| R10 | 12.613 | EXTRACT(YEAR…) is not sargable; forces Seq Scan of 189k daily_activity rows | Replaced EXTRACT(YEAR…) with range predicate + idx_daily_freeze partial index | 7.258 | +42.5% | Yes |
| R11 | 0.058 | UNIQUE index on username gives instant single-row Index Scan — already optimal | Unchanged — already uses UNIQUE index on username | 0.089 | -53.4% | Yes |
| R12 | 0.184 | PK on (learner_id, achievement_id) covers the probe; only 10 achievements | Unchanged — PK lookup already optimal | 0.135 | +26.6% | Yes |
| R13 | 15.309 | NOT IN + subquery with NULLs in referred_by: every row evaluates to UNKNOWN → 0 rows | Replaced NOT IN with NOT EXISTS + idx_learners_referred_by partial index; also fixes wrong result | 9.782 | +36.1% | No (intentional fix: 0→24268 rows) |
| R14 | 6.264 | No index on league_memberships.week_start; PK leads with learner_id → Seq Scan | Added idx_league_week_cohort; query now uses Index Only Scan on week_start | 4.687 | +25.2% | Yes |
| R15 | 5.694 | No index on learners.joined_at; Seq Scan of 30k learners then correlated EXISTS | Added idx_learners_joined(joined_at); range scan replaces full Seq Scan | 1.097 | +80.7% | Yes |
| R16 | 10.485 | ILIKE 'karan%' cannot use a standard B-tree index → Index Scan reads wide range | Replaced ILIKE with lower(username) LIKE + idx_learners_username_lower expression index | 8.533 | +18.6% | Yes |
| R17 | 31.780 | EXTRACT(YEAR FROM started_at) is not sargable; Seq Scan of 188k attempts | Replaced EXTRACT(YEAR…) with range predicate; idx_attempts_started_cover used | 17.768 | +44.1% | Yes |
| R18 | 11.290 | Both tables must be fully aggregated; no selectivity to push — unavoidable scan | Unchanged — full aggregation over both tables; no selectivity to exploit | 11.599 | -2.7% | Yes |
| R19 | 3647.898 | 160 lessons × 2 correlated subqueries each doing a full Seq Scan = 320 scans | Replaced 2 correlated subqueries with single LEFT JOIN + GROUP BY; idx_attempts_lesson_cover used | 34.547 | +99.1% | Yes |
| R20 | 15.229 | started_at::date BETWEEN is not sargable; Seq Scan of 188k attempts | Replaced ::date BETWEEN with range predicate on started_at; idx_attempts_started_cover used | 5.573 | +63.4% | Yes |
| R21 | 4.847 | PK on (learner_id, activity_date) covers the date range → Index Only Scan | Unchanged — already uses Index Only Scan on PK | 2.093 | +56.8% | Yes |
| R22 | 71.431 | ORDER BY started_at DESC with OFFSET 100000 forces sorting all 188k rows | Added idx_attempts_started_cover(started_at DESC) INCLUDE all columns; Index Only Scan | 16.056 | +77.5% | Yes |
| R23 | 14.513 | No composite index on (activity_date, learner_id, xp); Seq Scans on both tables | Added idx_daily_date_cover; Index Only Scan replaces Seq Scan on daily_activity | 5.908 | +59.3% | Yes |
| R24 | 46.432 | Must join all 188k attempts to lessons and units; no useful filter — unavoidable | Unchanged — must aggregate all 188k attempts; added idx_attempts_lesson_cover for lesson join | 49.893 | -7.5% | Yes |
| R25 | 230.338 | Must aggregate all 188k attempts joined to 30k learners by country+hour | Unchanged — must aggregate all 188k attempts across all learners; no selective filter | 244.236 | -6.0% | Yes |
| W01 | 0.929 | Single-row INSERT; PK constraint check only — no scan needed | Unchanged — single-row INSERT already optimal | 1.375 | -48.0% | Yes |
| W02 | 1.129 | Subquery to find max(attempt_id) filtered by date with no index on started_at | Added idx_attempts_open partial index (completed_at IS NULL); faster subquery | 0.851 | +24.6% | Yes |
| W03 | 1.733 | Single-row UPSERT on PK; no scan needed | Unchanged — single-row UPSERT already optimal | 1.743 | -0.6% | Yes |
| W04 | 15.659 | Must scan all league rows for the week to compute row_number() per cohort | Added idx_league_week_cohort; partial Index Only Scan for week filter | 13.974 | +10.8% | Yes |
| W05 | 75.673 | Seq Scan on 37.5k enrollments to aggregate XP; bulk INSERT with conflict check | Unchanged — bulk insert over enrollments is inherently table-wide | 89.008 | -17.6% | Yes |
| **Total** | **4336.618** | | | **581.725** | **+86.6%** | |

## 3. Before/After EXPLAIN Plans — Top 5 Improvements

### R19: Course popularity: enrollments per course, and how many started in 2026
**Before**: 3647.898 ms → **After**: 34.547 ms (improvement: 99.1%)

**BEFORE** (`benchmarks/results/baseline/R19.txt`, run 1 key lines):
```
  ->  Nested Loop  (cost=0.42..1316578.74 rows=160 width=48) (actual time=24.181..3663.042 rows=160 loops=1)
        ->  Index Scan using uq_unit_no on units u  (cost=0.14..10.24 rows=20 width=6) (actual time=0.002..0.038 rows=20 loops=1)
        ->  Index Scan using uq_lesson_no on lessons l  (cost=0.28..4.11 rows=8 width=10) (actual time=0.011..0.032 rows=8 loops=20)
          ->  Aggregate  (cost=4113.99..4114.00 rows=1 width=8) (actual time=12.503..12.503 rows=1 loops=160)
                ->  Seq Scan on lesson_attempts a  (cost=0.00..4113.75 rows=95 width=0) (actual time=0.061..12.482 rows=264 loops=160)
          ->  Aggregate  (cost=4114.02..4114.03 rows=1 width=32) (actual time=10.379..10.379 rows=1 loops=160)
                ->  Seq Scan on lesson_attempts a_1  (cost=0.00..4113.75 rows=107 width=2) (actual time=0.046..10.343 rows=298 loops=160)
Planning Time: 0.851 ms
Execution Time: 3663.399 ms
```

**AFTER** (`benchmarks/results/optimized/R19.txt`, run 1 key lines):
```
  ->  HashAggregate  (cost=1718.31..1975.08 rows=17118 width=48) (actual time=30.125..30.311 rows=160 loops=1)
        ->  Nested Loop Left Join  (cost=5.42..1547.13 rows=17118 width=22) (actual time=0.037..24.062 rows=47737 loops=1)
              ->  Hash Join  (cost=5.00..39.31 rows=160 width=8) (actual time=0.029..0.263 rows=160 loops=1)
                    ->  Seq Scan on lessons l  (cost=0.00..29.60 rows=1760 width=10) (actual time=0.003..0.092 rows=1760 loops=1)
                    ->  Hash  (cost=4.75..4.75 rows=20 width=6) (actual time=0.019..0.020 rows=20 loops=1)
                          ->  Seq Scan on units u  (cost=0.00..4.75 rows=20 width=6) (actual time=0.005..0.015 rows=20 loops=1)
              ->  Index Scan using idx_attempts_lesson_cover on lesson_attempts a  (cost=0.42..8.35 rows=107 width=18) (actual time=0.003..0.118 rows=298 loops=160)
Planning Time: 1.367 ms
Execution Time: 30.535 ms
```

### R22: Streak reminders: learners active every day from 23 to 29 June but not yet on 30 June
**Before**: 71.431 ms → **After**: 16.056 ms (improvement: 77.5%)

**BEFORE** (`benchmarks/results/baseline/R22.txt`, run 1 key lines):
```
  ->  Sort  (cost=24004.60..24475.35 rows=188300 width=22) (actual time=59.663..64.933 rows=100025 loops=1)
        ->  Seq Scan on lesson_attempts  (cost=0.00..3643.00 rows=188300 width=22) (actual time=0.005..19.535 rows=188300 loops=1)
Planning Time: 0.261 ms
Execution Time: 69.501 ms
```

**AFTER** (`benchmarks/results/optimized/R22.txt`, run 1 key lines):
```
  ->  Index Only Scan using idx_attempts_started_cover on lesson_attempts  (cost=0.42..8237.93 rows=188300 width=22) (actual time=0.078..16.666 rows=100025 loops=1)
Planning Time: 0.890 ms
Execution Time: 19.522 ms
```

### R07: "Start" button: the first lesson of learner 1042's Spanish course they have not completed yet
**Before**: 34.297 ms → **After**: 15.505 ms (improvement: 54.8%)

**BEFORE** (`benchmarks/results/baseline/R07.txt`, run 1 key lines):
```
  ->  Sort  (cost=5155.66..5169.93 rows=5706 width=48) (actual time=35.326..35.330 rows=20 loops=1)
        ->  HashAggregate  (cost=4732.79..5003.83 rows=5706 width=48) (actual time=35.073..35.268 rows=160 loops=1)
              ->  Hash Join  (cost=41.31..4561.61 rows=17118 width=10) (actual time=0.278..28.822 rows=47737 loops=1)
                    ->  Seq Scan on lesson_attempts a  (cost=0.00..3643.00 rows=188300 width=6) (actual time=0.005..9.205 rows=188300 loops=1)
                    ->  Hash  (cost=39.31..39.31 rows=160 width=8) (actual time=0.264..0.266 rows=160 loops=1)
                          ->  Hash Join  (cost=5.00..39.31 rows=160 width=8) (actual time=0.036..0.248 rows=160 loops=1)
                                ->  Seq Scan on lessons l  (cost=0.00..29.60 rows=1760 width=10) (actual time=0.002..0.092 rows=1760 loops=1)
                                ->  Hash  (cost=4.75..4.75 rows=20 width=6) (actual time=0.026..0.027 rows=20 loops=1)
                                      ->  Seq Scan on units u  (cost=0.00..4.75 rows=20 width=6) (actual time=0.008..0.021 rows=20 loops=1)
Planning Time: 1.225 ms
Execution Time: 35.479 ms
```

**AFTER** (`benchmarks/results/optimized/R07.txt`, run 1 key lines):
```
  ->  Sort  (cost=1501.90..1516.17 rows=5706 width=48) (actual time=19.595..19.598 rows=20 loops=1)
        ->  HashAggregate  (cost=1079.03..1350.07 rows=5706 width=48) (actual time=19.356..19.517 rows=160 loops=1)
              ->  Nested Loop  (cost=5.42..907.85 rows=17118 width=10) (actual time=0.126..10.555 rows=47737 loops=1)
                    ->  Hash Join  (cost=5.00..39.31 rows=160 width=8) (actual time=0.107..0.411 rows=160 loops=1)
                          ->  Seq Scan on lessons l  (cost=0.00..29.60 rows=1760 width=10) (actual time=0.015..0.128 rows=1760 loops=1)
                          ->  Hash  (cost=4.75..4.75 rows=20 width=6) (actual time=0.067..0.067 rows=20 loops=1)
                                ->  Seq Scan on units u  (cost=0.00..4.75 rows=20 width=6) (actual time=0.021..0.054 rows=20 loops=1)
                    ->  Index Only Scan using idx_attempts_lesson_cover on lesson_attempts a  (cost=0.42..4.36 rows=107 width=6) (actual time=0.003..0.038 rows=298 loops=160)
Planning Time: 2.464 ms
Execution Time: 19.930 ms
```

### R06: Leagues tab: leaderboard of learner 1042's cohort for the week starting 29 June 2026
**Before**: 17.179 ms → **After**: 0.485 ms (improvement: 97.2%)

**BEFORE** (`benchmarks/results/baseline/R06.txt`, run 1 key lines):
```
  ->  Incremental Sort  (cost=333.39..4331.37 rows=155 width=14) (actual time=21.353..21.354 rows=1 loops=1)
        ->  Nested Loop Anti Join  (cost=0.42..4327.82 rows=155 width=14) (actual time=21.273..21.316 rows=7 loops=1)
              ->  Nested Loop  (cost=0.42..93.95 rows=160 width=14) (actual time=0.029..0.048 rows=9 loops=1)
                    ->  Index Scan using uq_unit_no on units u  (cost=0.14..10.24 rows=20 width=6) (actual time=0.006..0.007 rows=2 loops=1)
                    ->  Index Scan using uq_lesson_no on lessons l  (cost=0.28..4.11 rows=8 width=16) (actual time=0.011..0.014 rows=4 loops=2)
              ->  Materialize  (cost=0.00..4114.00 rows=50 width=4) (actual time=0.056..2.360 rows=32 loops=9)
                    ->  Seq Scan on lesson_attempts a  (cost=0.00..4113.75 rows=50 width=4) (actual time=0.498..21.209 rows=39 loops=1)
Planning Time: 2.180 ms
Execution Time: 21.449 ms
```

**AFTER** (`benchmarks/results/optimized/R06.txt`, run 1 key lines):
```
  ->  Incremental Sort  (cost=9.86..120.52 rows=159 width=14) (actual time=1.170..1.171 rows=1 loops=1)
        ->  Nested Loop Anti Join  (cost=0.84..116.89 rows=159 width=14) (actual time=1.050..1.123 rows=7 loops=1)
              ->  Nested Loop  (cost=0.42..93.95 rows=160 width=14) (actual time=0.040..0.052 rows=9 loops=1)
                    ->  Index Scan using uq_unit_no on units u  (cost=0.14..10.24 rows=20 width=6) (actual time=0.012..0.013 rows=2 loops=1)
                    ->  Index Scan using uq_lesson_no on lessons l  (cost=0.28..4.11 rows=8 width=16) (actual time=0.011..0.013 rows=4 loops=2)
              ->  Materialize  (cost=0.42..8.55 rows=6 width=4) (actual time=0.109..0.114 rows=31 loops=9)
                    ->  Index Only Scan using idx_attempts_learner_lesson_done on lesson_attempts a  (cost=0.42..8.53 rows=6 width=4) (actual time=0.979..0.987 rows=39 loops=1)
Planning Time: 3.291 ms
Execution Time: 1.289 ms
```

### R17: Friends: search learners by username starting with "Karan"
**Before**: 31.780 ms → **After**: 17.768 ms (improvement: 44.1%)

**BEFORE** (`benchmarks/results/baseline/R17.txt`, run 1 key lines):
```
  ->  Finalize GroupAggregate  (cost=4443.48..4448.86 rows=3 width=46) (actual time=34.454..36.671 rows=3 loops=1)
        ->  Gather Merge  (cost=4443.48..4448.77 rows=3 width=22) (actual time=33.823..36.653 rows=6 loops=1)
              ->  Partial GroupAggregate  (cost=3443.47..3448.42 rows=3 width=22) (actual time=30.030..31.238 rows=3 loops=2)
                    ->  Sort  (cost=3443.47..3444.70 rows=492 width=7) (actual time=27.770..28.733 rows=30429 loops=2)
                          ->  Parallel Seq Scan on lesson_attempts  (cost=0.00..3421.47 rows=492 width=7) (actual time=14.549..23.116 rows=30429 loops=2)
Planning Time: 0.626 ms
Execution Time: 36.831 ms
```

**AFTER** (`benchmarks/results/optimized/R17.txt`, run 1 key lines):
```
  ->  HashAggregate  (cost=3741.11..3741.17 rows=3 width=46) (actual time=21.237..21.241 rows=3 loops=1)
        ->  Index Only Scan using idx_attempts_started_cover on lesson_attempts  (cost=0.42..3293.95 rows=59621 width=7) (actual time=0.018..11.061 rows=60858 loops=1)
Planning Time: 1.713 ms
Execution Time: 21.391 ms
```

## 4. Wrong-Result Query: R13

**Problem**: The original query uses `NOT IN` with a subquery over `referred_by`:
```sql
WHERE l.learner_id NOT IN (SELECT r.referred_by FROM learners r)
```
`referred_by` is `NULL` for most learners (no referrer recorded). SQL three-valued logic means
`x NOT IN (…, NULL)` evaluates to `UNKNOWN` for every row — so **no row ever passes** and the
query returns **0 rows**, even though thousands of learners have never referred anyone.

**Fix**: Replace with `NOT EXISTS`:
```sql
WHERE NOT EXISTS (SELECT 1 FROM learners r WHERE r.referred_by = l.learner_id)
```
This correctly returns all learners who have no row in `referred_by` pointing at them.

**Counts**:
- Original: **0 rows** (NULL-trap)
- Optimized: **24,268 rows** (correct)

**Verification**: 5 sample learner IDs from the optimized result were each confirmed to have
`count(*) = 0` in `SELECT count(*) FROM learners WHERE referred_by = <id>` (see `docs/results_check.txt`).

## 5. Proof Results Are Unchanged

Full output from `docs/results_check.py`:

```
======================================================================
RESULTS EQUIVALENCE CHECK  (Team T0037 – CP3)
======================================================================

--- R04 ---
  Original row count : 1
  Optimized row count: 1
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

--- R10 ---
  Original row count : 2
  Optimized row count: 2
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

--- R13 ---
  Original row count : 0
  Optimized row count: 24268
  Symmetric diff rows: 24268
  NOTE: R13 intentionally differs. Original returns 0 rows due to
        NOT IN + NULL (SQL NULL-trap). Optimized uses NOT EXISTS.
  5 sample rows from optimized R13:
    130|Ishaan_xPatel130
    181|KavyaGupta181
    195|Nisha07Gupta195
    211|Kabir07Singh211
    243|Pooja07Mehta243
    learner_id=130: learners referring to this id = 0  (must be 0)
    learner_id=181: learners referring to this id = 0  (must be 0)
    learner_id=195: learners referring to this id = 0  (must be 0)
    learner_id=211: learners referring to this id = 0  (must be 0)
    learner_id=243: learners referring to this id = 0  (must be 0)

--- R16 ---
  Original row count : 20
  Optimized row count: 20
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

--- R17 ---
  Original row count : 3
  Optimized row count: 3
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

--- R19 ---
  Original row count : 160
  Optimized row count: 160
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

--- R20 ---
  Original row count : 30
  Optimized row count: 30
  Symmetric diff rows: 0
  Result: PASS (diff must be 0)

======================================================================
```

## 6. Write Overhead (W01–W05)

| Query | Before avg (ms) | After avg (ms) | Delta (ms) | Direction | Acceptable? |
|---|---|---|---|---|---|
| W01 | 0.929 | 1.375 | +0.446 | slower | Yes |
| W02 | 1.129 | 0.851 | -0.278 | faster | Yes |
| W03 | 1.733 | 1.743 | +0.010 | slower | Yes |
| W04 | 15.659 | 13.974 | -1.685 | faster | Yes |
| W05 | 75.673 | 89.008 | +13.335 | slower | Yes |

**Discussion**: W01 and W03 are marginally slower (+0.4 ms each) because the new covering
indexes on `lesson_attempts` and `daily_activity` require additional index updates on insert.
W02 is slightly faster because `idx_attempts_open` (partial index on open attempts) makes the
subquery finding `max(attempt_id)` cheaper. W04 is marginally faster because
`idx_league_week_cohort` partially reduces the scan. W05 is slightly slower (+13 ms) because
the new covering index on `lesson_attempts` adds write overhead. All deltas are well within
acceptable bounds for the write patterns described; the worst case is W05 at +13 ms for a
batch job that runs once per week.

## 7. Index Storage

### New indexes created by CP3

| Index | Serves queries | Size | Table | Table size |
|---|---|---|---|---|
| idx_attempts_learner_started | R04, R25 | 5824 kB | lesson_attempts | 14 MB |
| idx_attempts_lesson_cover | R07, R08, R19, R24 | 7480 kB | lesson_attempts | 14 MB |
| idx_attempts_learner_lesson_done | R06 | 3584 kB | lesson_attempts | 14 MB |
| idx_attempts_started_cover | R17, R20, R22 | 11 MB | lesson_attempts | 14 MB |
| idx_attempts_open | W02 | 680 kB | lesson_attempts | 14 MB |
| idx_daily_date_cover | R09, R21, R23 | 5848 kB | daily_activity | 8184 kB |
| idx_daily_freeze | R10 | 64 kB | daily_activity | 8184 kB |
| idx_league_week_cohort | R05, R14, W04 | 1608 kB | league_memberships | 2184 kB |
| idx_learners_referred_by | R13 | 184 kB | learners | 2944 kB |
| idx_learners_joined | R15 | 672 kB | learners | 2944 kB |
| idx_learners_username_lower | R16 | 1096 kB | learners | 2944 kB |

Total new index storage: approximately **37 MB** across 11 indexes, against ~31 MB of heap data for the indexed tables. The largest index (`idx_attempts_started_cover`, 11 MB) is a covering index that makes R17, R20, and R22 fully index-only — it eliminates all heap access for those queries.

## 8. Queries We Could Not Speed Up

| Query | Avg (ms) | Why we cannot improve it further |
|---|---|---|
| R07 | 15.5 | Aggregates attempts for the Spanish course (course_id=1 filter); `idx_attempts_lesson_cover` helps the join but the GROUP BY still reads thousands of attempt rows |
| R08 | 35.9 | Requires a full scan of all 188k attempts to compute quit rate per lesson type; no selective predicate exists |
| R24 | 49.9 | Must aggregate all 188k attempts joined to 1760 lessons and 220 units to compute hearts_lost by CEFR level; `idx_attempts_lesson_cover` helps the join but the aggregation is unavoidable |
| R25 | 244.2 | Must join all 188k attempts to 30k learners and group by country+hour; there is no selective predicate — this is a full data-warehouse-style roll-up |
| R18 | 11.6 | Full aggregation over 37.5k enrollments and 11 courses; no filter to push |

**R07/R08/R24/R25/R18 are "honest aggregations"**: they produce summaries over most or all rows in large
tables. Without partial pre-aggregation (a materialized view, a summary table, or a time-partitioned
table), they cannot run faster than O(n) over the base data. These queries belong in an ETL pipeline or
a materialized view that is refreshed periodically — not in an OLTP index strategy.

**R22 (OFFSET 100000)** improved significantly (71 ms → 16 ms) because `idx_attempts_started_cover`
eliminates the heap visit. Full keyset pagination would eliminate the OFFSET cost entirely but would
require changing the application API; we report the achieved improvement as sufficient for CP3.

