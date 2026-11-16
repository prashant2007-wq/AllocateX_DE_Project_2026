SET search_path TO duolingo;

SELECT 'languages' t, count(*) FROM languages UNION ALL SELECT 'courses', count(*) FROM courses
UNION ALL SELECT 'units', count(*) FROM units UNION ALL SELECT 'lessons', count(*) FROM lessons
UNION ALL SELECT 'learners', count(*) FROM learners UNION ALL SELECT 'enrollments', count(*) FROM enrollments
UNION ALL SELECT 'lesson_attempts', count(*) FROM lesson_attempts UNION ALL SELECT 'daily_activity', count(*) FROM daily_activity
UNION ALL SELECT 'league_memberships', count(*) FROM league_memberships UNION ALL SELECT 'achievements', count(*) FROM achievements
UNION ALL SELECT 'learner_achievements', count(*) FROM learner_achievements;

SELECT count(*) AS attempts_outside_enrollment
FROM lesson_attempts a
JOIN lessons l ON l.lesson_id = a.lesson_id
JOIN units u ON u.unit_id = l.unit_id
WHERE NOT EXISTS (SELECT 1 FROM enrollments e WHERE e.learner_id = a.learner_id AND e.course_id = u.course_id);

SELECT cohort_id, week_start, count(*) FROM league_memberships GROUP BY 1,2 HAVING count(*) > 30;

SELECT count(*) AS mismatching_days
FROM daily_activity d
LEFT JOIN (SELECT learner_id, (started_at AT TIME ZONE 'Asia/Kolkata')::date AS day, sum(xp_earned) AS xp
           FROM lesson_attempts GROUP BY 1,2) a
  ON a.learner_id = d.learner_id AND a.day = d.activity_date
WHERE d.xp <> coalesce(a.xp, 0);

SELECT count(*) AS mismatching_enrollments
FROM enrollments e
LEFT JOIN (SELECT a.learner_id, u.course_id, sum(a.xp_earned) xp
           FROM lesson_attempts a JOIN lessons l ON l.lesson_id=a.lesson_id JOIN units u ON u.unit_id=l.unit_id
           GROUP BY 1,2) s ON s.learner_id=e.learner_id AND s.course_id=e.course_id
WHERE e.total_xp <> coalesce(s.xp,0);

SELECT tablename, indexname FROM pg_indexes WHERE schemaname='duolingo' ORDER BY 1,2;
