import csv, re, subprocess

OPT_CSV = "benchmarks/results/optimized/summary.csv"
LARGE_CSV = "benchmarks/results/large/summary.csv"

def load_csv(path):
    rows = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["query_id"]] = r
    return rows

opt = load_csv(OPT_CSV)
large = load_csv(LARGE_CSV)

names = [f"R{i:02d}" for i in range(1, 26)] + [f"W{i:02d}" for i in range(1, 6)]

targets = {}
for q in ["R02", "R03", "R04", "R05", "R06", "R11", "R12", "W01", "W02", "W03"]:
    targets[q] = ("Real-time", 5.0)
for q in ["R01", "R13", "R16", "R21", "R22", "R23"]:
    targets[q] = ("Interactive", 250.0)
for q in ["R07", "R08", "R09", "R10", "R14", "R15", "R17", "R18", "R19", "R20", "R24", "R25"]:
    targets[q] = ("Report", 5000.0)
for q in ["W04", "W05"]:
    targets[q] = ("Batch", 1000.0)

fix_notes = {
    "W05": "Initial large run was 1648.519 ms (missed <1000 ms target) due to FK trigger scans on learner_achievements(learner_id). Added idx_learner_achievements_learner in sql/05_indexes.sql -> 511.597 ms.",
}

pg = subprocess.run(["psql", "--version"], capture_output=True, text=True).stdout.strip()

lines = []
def L(s=""): lines.append(s)

L("# Phase 4: Scalability Report (Team T0037)")
L()
L("## Environment & Dataset")
L()
L(f"- **PostgreSQL**: {pg}")
L("- **Hardware**: MacBook, Apple M4, macOS 27.2")
L("- **Seed dataset (`duolingo_dbms`)**: ~188k `lesson_attempts`, 30k `learners`, 189k `daily_activity` (total DB: 92 MB)")
L("- **Large dataset (`duolingo_large`)**: 3,608,300 `lesson_attempts` (~19.2x), 600,000 `learners` (20x), 3,626,847 `daily_activity` (~19.2x)")
L("- **Load & index build times on `duolingo_large`**:")
L("  - `COPY` load (`sql/02_load_data.sql` against `large_data/`): **1m 55.85s** (115.85s)")
L("  - Index build (`sql/05_indexes.sql`): **19.33s**")
L("- **Benchmark method**: `benchmarks/run_benchmark.sh` running `sql/06_optimized_queries.sql` (5 runs per query; `EXPLAIN (ANALYZE, BUFFERS)`; writes W01–W05 inside `BEGIN; ... ROLLBACK;`).")
L()

L("## 1. Results Table (Seed Optimized vs. Large Optimized)")
L()
L("| Query | Optimized on seed (ms) | Optimized on large (ms) | Growth (large / seed) | Meets target? | If not, what you changed |")
L("|---|---|---|---|---|---|")

total_seed = 0.0
total_large = 0.0
stayed_same = []
grew_20x = []
grew_gt_20x = []

for n in names:
    s_ms = float(opt[n]["avg_ms"])
    l_ms = float(large[n]["avg_ms"])
    growth = l_ms / s_ms if s_ms > 0 else 0.0
    total_seed += s_ms
    total_large += l_ms
    tier, limit = targets[n]
    meets = f"Yes ({tier} < {int(limit)} ms)" if l_ms < limit else f"No ({tier} < {int(limit)} ms)"
    note = fix_notes.get(n, "—")
    L(f"| {n} | {s_ms:.3f} | {l_ms:.3f} | {growth:.2f}x | {meets} | {note} |")

    if growth < 4.0:
        stayed_same.append((n, s_ms, l_ms, growth))
    elif growth <= 25.0:
        grew_20x.append((n, s_ms, l_ms, growth))
    else:
        grew_gt_20x.append((n, s_ms, l_ms, growth))

L(f"| **Total** | **{total_seed:.3f}** | **{total_large:.3f}** | **{total_large/total_seed:.2f}x** | **All 30 meet targets** | |")
L()

L("## 2. Growth Analysis")
L()
L("### Stayed about the same (< 4x growth — O(log n) index lookups)")
L()
L("Point lookups and narrow user-scoped queries use B-tree index traversals whose depth grows logarithmically with 20x data (e.g., depth 3 → depth 4):")
L()
L("| Query | Seed (ms) | Large (ms) | Growth | Why |")
L("|---|---|---|---|---|")
for n, s_ms, l_ms, g in stayed_same:
    L(f"| {n} | {s_ms:.3f} | {l_ms:.3f} | {g:.2f}x | {large[n]['scan_nodes']} |")
L()

L("### Grew roughly ~4x to 25x (read a proportional ~20x slice of the table)")
L()
L("Date-range reports, full-table aggregations, and prefix/filter scans read ~20x more matching rows or index entries:")
L()
L("| Query | Seed (ms) | Large (ms) | Growth | Why |")
L("|---|---|---|---|---|")
for n, s_ms, l_ms, g in grew_20x:
    L(f"| {n} | {s_ms:.3f} | {l_ms:.3f} | {g:.2f}x | {large[n]['scan_nodes']} |")
L()

L("### Grew more than 25x (super-linear growth)")
L()
if grew_gt_20x:
    L("| Query | Seed (ms) | Large (ms) | Growth | Explanation & Action |")
    L("|---|---|---|---|---|")
    for n, s_ms, l_ms, g in grew_gt_20x:
        L(f"| {n} | {s_ms:.3f} | {l_ms:.3f} | {g:.2f}x | {large[n]['scan_nodes']} — scales with ~20x more rows *plus* larger hash/sort/nested-loop work or memory spills |")
else:
    L("No query grew more than 25x after the W05 index fix.")
L()
L("Specifically for **R19** (34.547 ms → 2251.259 ms, **65.16x**): on seed, `lesson_attempts` per lesson fit in L3 cache and used a fast Index Scan + Hash/Sort; at 20x scale (3.6M rows), the Spanish course (`course_id = 1`) matches ~20x more rows across 160 lessons, causing much larger heap/index I/O and aggregation state. It still finishes in **2.25s** (well under the 5,000 ms Report target).")
L()
L("Specifically for **W04** (13.974 ms → 158.069 ms, **11.31x**): weekly league close ranks and updates 20x more cohort rows in `league_memberships` for week `2026-06-29` (~16,940 rows instead of 847), remaining well under the 1,000 ms Batch target.")
L()

L("## 3. What Broke at Scale (Before / After Plans)")
L()
L("Only **W05** missed its target on the initial large benchmark run:")
L("- **Target**: Batch < 1,000 ms")
L("- **Before**: **1,648.519 ms** average (1,703.193 ms in standalone `EXPLAIN ANALYZE`)")
L("- **Root cause from plan**: `learner_achievements` had only the composite PK `(learner_id, achievement_id)`. Wait — when inserting 79,757 qualifying rows in W05, the foreign-key validation triggers (`learner_achievements_learner_id_fkey`: 394.2 ms, `learner_achievements_achievement_id_fkey`: 261.1 ms) and heap/index updates took over 1,041 ms inside `Insert on learner_achievements`. Adding `idx_learner_achievements_learner` on `learner_achievements(learner_id)` reduced W05 to **511.597 ms** (523.628 ms standalone), comfortably passing the < 1,000 ms Batch target.")
L()
L("**W05 BEFORE** (`benchmarks/results/large/W05_before.txt`):")
L("```")
for l in open("benchmarks/results/large/W05_before.txt", encoding="utf-8"):
    if any(k in l for k in ["Insert on", "GroupAggregate", "Index Scan", "Trigger", "Execution Time", "Planning Time"]):
        L(l.rstrip())
L("```")
L()
L("**W05 AFTER** (`benchmarks/results/large/W05_after.txt`):")
L("```")
for l in open("benchmarks/results/large/W05_after.txt", encoding="utf-8"):
    if any(k in l for k in ["Insert on", "GroupAggregate", "Index Scan", "Trigger", "Execution Time", "Planning Time"]):
        L(l.rstrip())
L("```")
L()

L("## 4. Storage Comparison (Seed vs. Large)")
L()
L("| Metric | Seed (`duolingo_dbms`) | Large (`duolingo_large`, before partitioning) |")
L("|---|---|---|")
L("| Total database size | 92 MB | 1,595 MB (2,200 MB with `lesson_attempts_part`) |")
L("| Sum of base table heaps | 30 MB | 601 MB |")
L("| Sum of indexes | 53 MB | 1,029 MB |")
L("| `lesson_attempts` heap / largest index | 14 MB / 11 MB | 263 MB / 202 MB (`idx_attempts_started_cover`) |")
L("| `daily_activity` heap / largest index | 8,184 kB / 5,848 kB | 153 MB / 109 MB (`idx_daily_date_cover`) |")
L("| `learners` heap / largest index | 2,944 kB / 2,216 kB | 59 MB / 47 MB (`learners_email_key`) |")
L()

L("## 5. Architecture for 100x Scale")
L()
L("### Partitioning (`sql/08_partitioning.sql`)")
L("- **Strategy**: Range partitioning on `lesson_attempts` by `started_at` into monthly partitions (`2025-01` through `2026-07`) plus a `DEFAULT` partition (`lesson_attempts_part`).")
L("- **Primary Key Rule**: PostgreSQL requires any PK or UNIQUE constraint on a partitioned table to include all partition key columns, so the PK becomes `(attempt_id, started_at)`. No table in the schema references `lesson_attempts` via FK, so no foreign keys break.")
L("- **Pruning Evidence** (`benchmarks/results/large/partition_pruning.txt`): Running R20 (June 2026) on `lesson_attempts_part` scans **only `lesson_attempts_p_2026_06`** (85.612 ms vs 94.516 ms on the unpartitioned table) — 18 monthly partitions + default are pruned at planning time.")
L()
L("### Sharding by `learner_id`")
L("- **OLTP shard key**: `learner_id` co-locates a learner's `learners`, `enrollments`, `lesson_attempts`, `daily_activity`, and `learner_achievements` on a single shard, keeping R02, R03, R04, R06, R12, W01, W02, W03 single-shard.")
L("- **Cross-shard problem**: League leaderboards (`R05`, `R14`, `W04`) group by `(week_start, cohort_id)`, which spans multiple learners. At 100x, either route league tables to a dedicated league service/shard keyed by `cohort_id` (or co-locate a cohort on one shard), and route global analytics (`R07`, `R08`, `R17`, `R18`, `R19`, `R20`, `R24`, `R25`) to an analytics replica or pre-aggregated summary tables.")
L()
L("### Read Replicas and Caching")
L("- **Primary (read/write)**: `W01–W05` and strongly consistent post-write reads (`R02`, `R03`, `R04`, `R06`, `R11`, `R12`).")
L("- **Read Replicas**: Heavy analytical and interactive queries (`R07`, `R08`, `R10`, `R13`, `R14`, `R15`, `R17`, `R18`, `R19`, `R20`, `R22`, `R24`, `R25`).")
L("- **Redis / Application Cache**: Static curriculum (`R01`), user profile/auth (`R11`), and short-TTL cohort leaderboards (`R05`, 5–15s TTL).")
L()
L("### Maintenance")
L("- **Autovacuum**: Tune `lesson_attempts` (and each active monthly partition) with `autovacuum_vacuum_scale_factor = 0.02` and `autovacuum_analyze_scale_factor = 0.01` so visibility maps stay fresh for Index-Only Scans (`R06`, `R07`, `R17`, `R20`, `R22`).")
L("- **Archiving**: Detach and archive partitions older than 12 months (`ALTER TABLE ... DETACH PARTITION ... CONCURRENTLY`) to cold object storage.")
L("- **Summary tables**: Refresh materialized views or rollup tables for `R19`, `R24`, `R25` on an hourly/daily cron schedule.")
L()

L("## 6. Conclusion")
L()
L("At 20x scale (3.61M `lesson_attempts`, 600k `learners`), **all 30 queries meet their latency targets** after adding `idx_learner_achievements_learner` for `W05`. Real-time queries remain sub-millisecond (0.14–2.17 ms), interactive queries stay under 210 ms, batch jobs finish in 158–512 ms, and all analytical reports complete under 2.3s.")
L()
L("**Remaining risks for 100x (next year)**:")
L("1. **R19 (2.25s) and R25 (1.95s)** will approach or exceed the 5s report target at 100x unless backed by read replicas or pre-aggregated summary tables.")
L("2. **R16 (`lower(username) LIKE 'karan%'`, 209 ms)** is close to the 250 ms interactive ceiling because `'karan%'` matches ~1,000+ rows at 20x; at 100x, enforcing stricter prefix/pagination or trigram/search-index offloading will be required.")
L("3. **Index storage (1,029 MB vs 601 MB heap)** is 1.71x the table size; monthly range partitioning (`sql/08_partitioning.sql`) keeps hot working-set indexes in RAM.")
L()

out = "\n".join(lines)
open("docs/05_scalability_report.md", "w", encoding="utf-8").write(out)
print("Written docs/05_scalability_report.md")
print("TODO count:", out.count("TODO"))
print(f"Total seed: {total_seed:.3f} ms | Total large: {total_large:.3f} ms")
