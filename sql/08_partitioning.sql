-- =====================================================================
-- CP4: sql/08_partitioning.sql (Team T0037)
--
-- Primary Key Rule for Partitioned Tables in PostgreSQL:
--   A PRIMARY KEY or UNIQUE constraint on a partitioned table MUST include
--   all partition key columns. Therefore, the PK on lesson_attempts_part
--   becomes (attempt_id, started_at) instead of (attempt_id) alone.
--   No other table in the schema references lesson_attempts via a foreign key,
--   so changing the PK to include started_at does not break any FK.
--
-- Run on duolingo_large only. Keeps the original lesson_attempts table intact.
-- =====================================================================
SET search_path TO duolingo;

DROP TABLE IF EXISTS lesson_attempts_part CASCADE;

CREATE TABLE lesson_attempts_part (
    LIKE lesson_attempts INCLUDING DEFAULTS INCLUDING CONSTRAINTS,
    PRIMARY KEY (attempt_id, started_at)
) PARTITION BY RANGE (started_at);

ALTER TABLE lesson_attempts_part
    ADD CONSTRAINT fk_part_learner
        FOREIGN KEY (learner_id) REFERENCES learners(learner_id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_part_lesson
        FOREIGN KEY (lesson_id) REFERENCES lessons(lesson_id) ON DELETE RESTRICT;

DO $$
DECLARE
    m DATE := DATE '2025-01-01';
    m_end DATE;
    part_name TEXT;
    bound_start TEXT;
    bound_end TEXT;
BEGIN
    WHILE m <= DATE '2026-07-01' LOOP
        m_end := (m + INTERVAL '1 month')::DATE;
        part_name := format('lesson_attempts_p_%s', to_char(m, 'YYYY_MM'));
        bound_start := to_char(m, 'YYYY-MM-DD') || ' 00:00:00+05:30';
        bound_end   := to_char(m_end, 'YYYY-MM-DD') || ' 00:00:00+05:30';

        EXECUTE format(
            'CREATE TABLE %I PARTITION OF lesson_attempts_part FOR VALUES FROM (%L) TO (%L)',
            part_name, bound_start, bound_end
        );
        m := m_end;
    END LOOP;
END $$;

CREATE TABLE lesson_attempts_p_default PARTITION OF lesson_attempts_part DEFAULT;

INSERT INTO lesson_attempts_part
SELECT * FROM lesson_attempts;

CREATE INDEX idx_part_attempts_learner_started
    ON lesson_attempts_part (learner_id, started_at);

CREATE INDEX idx_part_attempts_started_desc
    ON lesson_attempts_part (started_at DESC);

ANALYZE lesson_attempts_part;
