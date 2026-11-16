DROP SCHEMA IF EXISTS duolingo CASCADE;
CREATE SCHEMA duolingo;
SET search_path TO duolingo;

CREATE TABLE languages (
  language_code CHAR(2) PRIMARY KEY,
  language_name VARCHAR(50) NOT NULL UNIQUE,
  CONSTRAINT chk_lang_code CHECK (language_code ~ '^[a-z]{2}$')
);

CREATE TABLE courses (
  course_id     INTEGER PRIMARY KEY,
  from_lang     CHAR(2) NOT NULL REFERENCES languages(language_code) ON DELETE RESTRICT,
  learning_lang CHAR(2) NOT NULL REFERENCES languages(language_code) ON DELETE RESTRICT,
  title         VARCHAR(100) NOT NULL,
  launched_on   DATE NOT NULL,
  CONSTRAINT uq_course_pair UNIQUE (from_lang, learning_lang),
  CONSTRAINT chk_course_langs_differ CHECK (from_lang <> learning_lang)
);

CREATE TABLE units (
  unit_id    INTEGER PRIMARY KEY,
  course_id  INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
  unit_no    SMALLINT NOT NULL,
  title      VARCHAR(100) NOT NULL,
  cefr_level CHAR(2) NOT NULL,
  CONSTRAINT uq_unit_no UNIQUE (course_id, unit_no),
  CONSTRAINT chk_unit_no CHECK (unit_no > 0),
  CONSTRAINT chk_cefr CHECK (cefr_level IN ('A1','A2','B1','B2','C1','C2'))
);

CREATE TABLE lessons (
  lesson_id   INTEGER PRIMARY KEY,
  unit_id     INTEGER NOT NULL REFERENCES units(unit_id) ON DELETE CASCADE,
  lesson_no   SMALLINT NOT NULL,
  lesson_type VARCHAR(20) NOT NULL,
  xp_value    SMALLINT NOT NULL,
  CONSTRAINT uq_lesson_no UNIQUE (unit_id, lesson_no),
  CONSTRAINT chk_lesson_no CHECK (lesson_no > 0),
  CONSTRAINT chk_lesson_type CHECK (lesson_type IN ('LEARN','PRACTICE','STORY','LEGENDARY')),
  CONSTRAINT chk_xp_value CHECK (xp_value > 0)
);

CREATE TABLE learners (
  learner_id    INTEGER PRIMARY KEY,
  username      VARCHAR(50) NOT NULL UNIQUE,
  email         VARCHAR(100) NOT NULL UNIQUE,
  country_code  CHAR(2) NOT NULL,
  daily_goal_xp SMALLINT NOT NULL,
  subscription  VARCHAR(10) NOT NULL DEFAULT 'FREE',
  referred_by   INTEGER REFERENCES learners(learner_id) ON DELETE SET NULL,
  joined_at     TIMESTAMPTZ NOT NULL,
  CONSTRAINT chk_username CHECK (username ~ '^[A-Za-z0-9_]+$'),
  CONSTRAINT chk_email CHECK (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
  CONSTRAINT chk_country CHECK (country_code ~ '^[A-Z]{2}$'),
  CONSTRAINT chk_daily_goal CHECK (daily_goal_xp IN (10,20,30,50)),
  CONSTRAINT chk_subscription CHECK (subscription IN ('FREE','SUPER','MAX')),
  CONSTRAINT chk_no_self_referral CHECK (referred_by IS NULL OR referred_by <> learner_id)
);

CREATE TABLE enrollments (
  learner_id  INTEGER NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
  course_id   INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
  enrolled_at TIMESTAMPTZ NOT NULL,
  total_xp    INTEGER NOT NULL DEFAULT 0,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  PRIMARY KEY (learner_id, course_id),
  CONSTRAINT chk_total_xp CHECK (total_xp >= 0)
);

CREATE TABLE lesson_attempts (
  attempt_id   INTEGER PRIMARY KEY,
  learner_id   INTEGER NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
  lesson_id    INTEGER NOT NULL REFERENCES lessons(lesson_id) ON DELETE RESTRICT,
  started_at   TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  mistakes     SMALLINT NOT NULL DEFAULT 0,
  hearts_lost  SMALLINT NOT NULL DEFAULT 0,
  xp_earned    SMALLINT NOT NULL DEFAULT 0,
  is_perfect   BOOLEAN NOT NULL DEFAULT FALSE,
  device       VARCHAR(10) NOT NULL,
  CONSTRAINT chk_mistakes CHECK (mistakes >= 0),
  CONSTRAINT chk_hearts CHECK (hearts_lost >= 0 AND hearts_lost <= mistakes),
  CONSTRAINT chk_xp_earned CHECK (xp_earned >= 0),
  CONSTRAINT chk_perfect CHECK (NOT is_perfect OR mistakes = 0),
  CONSTRAINT chk_quit_no_xp CHECK (completed_at IS NOT NULL OR xp_earned = 0),
  CONSTRAINT chk_time_order CHECK (completed_at IS NULL OR completed_at >= started_at),
  CONSTRAINT chk_device CHECK (device IN ('ANDROID','IOS','WEB'))
);

CREATE TABLE daily_activity (
  learner_id         INTEGER NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
  activity_date      DATE NOT NULL,
  xp                 INTEGER NOT NULL DEFAULT 0,
  lessons_completed  SMALLINT NOT NULL DEFAULT 0,
  used_streak_freeze BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (learner_id, activity_date),
  CONSTRAINT chk_da_xp CHECK (xp >= 0),
  CONSTRAINT chk_da_lessons CHECK (lessons_completed >= 0),
  CONSTRAINT chk_freeze_zero_xp CHECK (NOT used_streak_freeze OR xp = 0)
);

CREATE TABLE league_memberships (
  learner_id INTEGER NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  tier       VARCHAR(12) NOT NULL,
  cohort_id  INTEGER NOT NULL,
  weekly_xp  INTEGER NOT NULL DEFAULT 0,
  final_rank SMALLINT,
  result     VARCHAR(10),
  PRIMARY KEY (learner_id, week_start),
  CONSTRAINT chk_week_monday CHECK (EXTRACT(ISODOW FROM week_start) = 1),
  CONSTRAINT chk_tier CHECK (tier IN ('BRONZE','SILVER','GOLD','SAPPHIRE','RUBY','EMERALD','AMETHYST','PEARL','OBSIDIAN','DIAMOND')),
  CONSTRAINT chk_weekly_xp CHECK (weekly_xp >= 0),
  CONSTRAINT chk_rank_range CHECK (final_rank IS NULL OR final_rank BETWEEN 1 AND 30),
  CONSTRAINT chk_result CHECK (result IS NULL OR result IN ('PROMOTED','DEMOTED','STAYED')),
  CONSTRAINT chk_rank_result_together CHECK ((final_rank IS NULL) = (result IS NULL))
);

CREATE TABLE achievements (
  achievement_id INTEGER PRIMARY KEY,
  code           VARCHAR(30) NOT NULL UNIQUE,
  name           VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE learner_achievements (
  learner_id     INTEGER NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
  achievement_id INTEGER NOT NULL REFERENCES achievements(achievement_id) ON DELETE RESTRICT,
  earned_at      TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (learner_id, achievement_id)
);
