-- ============================================================
-- CP3: sql/05_indexes.sql  (Team T0037)
-- Run after sql/01_schema.sql + sql/02_load_data.sql
-- Do NOT add any index not listed here without updating the report.
-- ============================================================
SET search_path TO duolingo;

-- R04: equality on learner_id + range on started_at replaces DATE() trick that blocked indexes
-- R25: covers (learner_id, started_at) so lessons-per-hour-per-country can skip the heap
CREATE INDEX idx_attempts_learner_started
    ON lesson_attempts (learner_id, started_at);

-- R07, R08, R19, R24: joins/groups by lesson_id; INCLUDE columns avoid heap visits
--   completed_at and mistakes are read by most of these queries
CREATE INDEX idx_attempts_lesson_cover
    ON lesson_attempts (lesson_id)
    INCLUDE (completed_at, mistakes, hearts_lost, xp_earned);

-- R06: NOT EXISTS probe on completed attempts only; tiny partial index
CREATE INDEX idx_attempts_learner_lesson_done
    ON lesson_attempts (learner_id, lesson_id)
    WHERE completed_at IS NOT NULL;

-- R17, R20, R22: time-ordered scans; covering all selected columns avoids heap
--   R22 OFFSET 100000 still needs a full index scan; this avoids touching the table
CREATE INDEX idx_attempts_started_cover
    ON lesson_attempts (started_at DESC)
    INCLUDE (attempt_id, learner_id, lesson_id, xp_earned, device, is_perfect, completed_at);

-- W02: finds unfinished attempts of one day; small partial index (completed_at IS NULL rows only)
CREATE INDEX idx_attempts_open
    ON lesson_attempts (started_at)
    INCLUDE (attempt_id)
    WHERE completed_at IS NULL;

-- R09, R21, R23: date range filter + xp check; covering learner_id avoids heap for joins
CREATE INDEX idx_daily_date_cover
    ON daily_activity (activity_date)
    INCLUDE (learner_id, xp, used_streak_freeze);

-- R10: only freeze days (used_streak_freeze = TRUE) are queried; very small partial index
CREATE INDEX idx_daily_freeze
    ON daily_activity (activity_date, learner_id)
    WHERE used_streak_freeze;

-- R05, R14, W04: PK leads with learner_id but queries filter by week_start + cohort_id
--   covering weekly_xp, tier, result avoids heap for leaderboard and close queries
CREATE INDEX idx_league_week_cohort
    ON league_memberships (week_start, cohort_id)
    INCLUDE (learner_id, weekly_xp, tier, result, final_rank);

-- R13: NOT EXISTS probe on referred_by; partial index skips the NULLs
CREATE INDEX idx_learners_referred_by
    ON learners (referred_by)
    WHERE referred_by IS NOT NULL;

-- R15: range filter on joined_at for retention query
CREATE INDEX idx_learners_joined
    ON learners (joined_at);

-- R16: expression index for case-insensitive prefix search
--   query rewritten to lower(username) LIKE 'karan%' with text_pattern_ops
CREATE INDEX idx_learners_username_lower
    ON learners (lower(username) text_pattern_ops);

-- W05: FK trigger on learner_achievements.learner_id scans the table without this index;
--   at large scale (750k+ inserts) this adds ~400ms of trigger overhead
CREATE INDEX idx_learner_achievements_learner
    ON learner_achievements (learner_id);
