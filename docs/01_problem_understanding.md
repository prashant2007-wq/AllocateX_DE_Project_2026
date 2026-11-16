# Phase 1: Problem Understanding (Team T0037)

| # | Business need (own words) | Stakeholder | Type |
|---|---|---|---|
| P1 | Home screen (course path, XP, goal ring, next lesson, streak) must open instantly | Learner | Customer-facing / real-time |
| P2 | Leagues tab must show the leaderboard fast; weekly close must finish quickly | Leagues/gamification team | Leaderboard: real-time; weekly close: batch |
| P3 | Starting/finishing a lesson and updating daily XP must not lag | Learner | Customer-facing / real-time |
| P4 | Reports on hard lessons, quit rate, hearts lost, completion | Curriculum team | Reporting / analytics |
| P5 | Referral list of learners with no referrals is wrongly empty; needs correct results | Growth | Reporting (interactive tool) |
| P6 | DAU, retention, streak reminders, XP trends, course popularity dashboards time out | Growth & retention, notifications | Reporting / analytics |
| P7 | Sign-in, friend search, achievements, support console slow; data will grow 20x | Platform, monetisation (Super/Max), support | Sign-in/friend search/achievements: real-time; support console: interactive; monetisation: reporting |

## Assumptions
- Seed export is correct unless a constraint shows otherwise.
- All timestamps are IST (+05:30); the "current date" is 30 June 2026.
- Real-time queries target <5 ms, interactive <250 ms, reports <5 s, batch <1 s.
- 20x growth keeps the same access patterns.
