import subprocess, sys

def run(sql, label=""):
    r = subprocess.run(
        ["psql", "-d", "duolingo_dbms", "-v", "ON_ERROR_STOP=1", "-X", "-A", "-t", "-c", sql],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(f"ERROR in {label}: {r.stderr}")
        sys.exit(1)
    return r.stdout.strip()

checks = [
    # (label, orig_sql, opt_sql, expect_equal)
    (
        "R04",
        """SELECT l.daily_goal_xp, coalesce(sum(a.xp_earned), 0) AS xp_today
FROM duolingo.learners l
LEFT JOIN duolingo.lesson_attempts a ON a.learner_id = l.learner_id AND DATE(a.started_at) = '2026-06-30'
WHERE l.learner_id = 1042 GROUP BY l.daily_goal_xp""",
        """SELECT l.daily_goal_xp, coalesce(sum(a.xp_earned), 0) AS xp_today
FROM duolingo.learners l
LEFT JOIN duolingo.lesson_attempts a ON a.learner_id = l.learner_id
    AND a.started_at >= '2026-06-30' AND a.started_at < '2026-07-01'
WHERE l.learner_id = 1042 GROUP BY l.daily_goal_xp""",
        True
    ),
    (
        "R10",
        """SELECT l.subscription, count(*) AS freezes_used
FROM duolingo.daily_activity d JOIN duolingo.learners l ON l.learner_id = d.learner_id
WHERE d.used_streak_freeze AND EXTRACT(YEAR FROM d.activity_date) = 2026
GROUP BY l.subscription ORDER BY freezes_used DESC""",
        """SELECT l.subscription, count(*) AS freezes_used
FROM duolingo.daily_activity d JOIN duolingo.learners l ON l.learner_id = d.learner_id
WHERE d.used_streak_freeze AND d.activity_date >= '2026-01-01' AND d.activity_date < '2027-01-01'
GROUP BY l.subscription ORDER BY freezes_used DESC""",
        True
    ),
    (
        "R13",
        """SELECT l.learner_id, l.username FROM duolingo.learners l
WHERE l.learner_id NOT IN (SELECT r.referred_by FROM duolingo.learners r)""",
        """SELECT l.learner_id, l.username FROM duolingo.learners l
WHERE NOT EXISTS (SELECT 1 FROM duolingo.learners r WHERE r.referred_by = l.learner_id)""",
        False  # intentionally different: original returns 0 rows due to NULL trap
    ),
    (
        "R16",
        """SELECT learner_id, username, country_code FROM duolingo.learners
WHERE username ILIKE 'karan%' ORDER BY username LIMIT 20""",
        """SELECT learner_id, username, country_code FROM duolingo.learners
WHERE lower(username) LIKE 'karan%' ORDER BY username LIMIT 20""",
        True
    ),
    (
        "R17",
        """SELECT device, count(*) AS completed,
round(100.0 * count(*) FILTER (WHERE is_perfect) / count(*), 2) AS perfect_pct
FROM duolingo.lesson_attempts WHERE completed_at IS NOT NULL AND EXTRACT(YEAR FROM started_at) = 2026
GROUP BY device ORDER BY perfect_pct DESC""",
        """SELECT device, count(*) AS completed,
round(100.0 * count(*) FILTER (WHERE is_perfect) / count(*), 2) AS perfect_pct
FROM duolingo.lesson_attempts WHERE completed_at IS NOT NULL
  AND started_at >= '2026-01-01' AND started_at < '2027-01-01'
GROUP BY device ORDER BY perfect_pct DESC""",
        True
    ),
    (
        "R19",
        """SELECT l.lesson_id, u.unit_no, l.lesson_no,
(SELECT count(*) FROM duolingo.lesson_attempts a WHERE a.lesson_id = l.lesson_id AND a.completed_at IS NOT NULL) AS completions,
(SELECT round(avg(a.mistakes), 2) FROM duolingo.lesson_attempts a WHERE a.lesson_id = l.lesson_id) AS avg_mistakes
FROM duolingo.lessons l JOIN duolingo.units u ON u.unit_id = l.unit_id
WHERE u.course_id = 1 ORDER BY u.unit_no, l.lesson_no""",
        """SELECT l.lesson_id, u.unit_no, l.lesson_no,
count(a.attempt_id) FILTER (WHERE a.completed_at IS NOT NULL) AS completions,
round(avg(a.mistakes), 2) AS avg_mistakes
FROM duolingo.lessons l JOIN duolingo.units u ON u.unit_id = l.unit_id
LEFT JOIN duolingo.lesson_attempts a ON a.lesson_id = l.lesson_id
WHERE u.course_id = 1 GROUP BY l.lesson_id, u.unit_no, l.lesson_no
ORDER BY u.unit_no, l.lesson_no""",
        True
    ),
    (
        "R20",
        """SELECT day, xp, sum(xp) OVER (ORDER BY day) AS running_xp FROM (
SELECT started_at::date AS day, sum(xp_earned) AS xp FROM duolingo.lesson_attempts
WHERE started_at::date BETWEEN '2026-06-01' AND '2026-06-30' GROUP BY 1) d ORDER BY day""",
        """SELECT day, xp, sum(xp) OVER (ORDER BY day) AS running_xp FROM (
SELECT started_at::date AS day, sum(xp_earned) AS xp FROM duolingo.lesson_attempts
WHERE started_at >= '2026-06-01' AND started_at < '2026-07-01' GROUP BY 1) d ORDER BY day""",
        True
    ),
]

lines = ["=" * 70, "RESULTS EQUIVALENCE CHECK  (Team T0037 – CP3)", "=" * 70, ""]

for label, orig, opt, expect_equal in checks:
    cnt_orig = run(f"SELECT count(*) FROM ({orig}) t", f"{label} orig count")
    cnt_opt  = run(f"SELECT count(*) FROM ({opt}) t",  f"{label} opt count")

    diff_sql = f"""
(SELECT * FROM ({orig}) orig EXCEPT SELECT * FROM ({opt}) opt)
UNION ALL
(SELECT * FROM ({opt}) opt EXCEPT SELECT * FROM ({orig}) orig)
"""
    diff_rows = run(f"SELECT count(*) FROM ({diff_sql}) d", f"{label} diff")

    lines.append(f"--- {label} ---")
    lines.append(f"  Original row count : {cnt_orig}")
    lines.append(f"  Optimized row count: {cnt_opt}")
    lines.append(f"  Symmetric diff rows: {diff_rows}")

    if label == "R13":
        lines.append(f"  NOTE: R13 intentionally differs. Original returns 0 rows due to")
        lines.append(f"        NOT IN + NULL (SQL NULL-trap). Optimized uses NOT EXISTS.")
        # Show 5 sample optimized rows and verify they have no referrals
        sample = run(f"SELECT learner_id, username FROM ({opt}) t LIMIT 5")
        lines.append(f"  5 sample rows from optimized R13:")
        for row in sample.split("\n")[:5]:
            lines.append(f"    {row}")
        # Verify none of these appear as a referred_by
        ids = [r.split("|")[0].strip() for r in sample.split("\n") if "|" in r]
        for lid in ids:
            check = run(
                f"SELECT count(*) FROM duolingo.learners WHERE referred_by = {lid}",
                f"R13 verify {lid}"
            )
            lines.append(f"    learner_id={lid}: learners referring to this id = {check}  (must be 0)")
    elif expect_equal:
        status = "PASS" if diff_rows == "0" else "FAIL"
        lines.append(f"  Result: {status} (diff must be 0)")
    lines.append("")

lines.append("=" * 70)
out = "\n".join(lines)
print(out)
open("docs/results_check.txt", "w").write(out + "\n")
print("Written docs/results_check.txt")
