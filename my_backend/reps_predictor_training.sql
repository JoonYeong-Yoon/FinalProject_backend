-- reps_predictor_training.sql
SELECT
    adl.reps_done                         AS target_reps,

    u.gender,
    u.goal,
    u.fitness_level,
    ubi.bmi,
    ubi.body_fat,
    ubi.skeletal_muscle,
    ubi.weight_kg                         AS user_current_weight,

    adl.exercise_id,
    e.category_1                          AS exercise_category,

    prev_adl.reps_done                    AS previous_set_reps,
    prev_adl.score                        AS previous_set_score

FROM activity_detail_logs adl
JOIN activity_logs al
    ON adl.activity_id = al.id
JOIN users u
    ON al.user_id = u.id
JOIN exercise e
    ON adl.exercise_id = e.id
JOIN (
    SELECT DISTINCT ON (user_id)
        user_id, bmi, body_fat, skeletal_muscle, weight_kg
    FROM user_body_info
    ORDER BY user_id, updated_at DESC
) ubi ON u.id = ubi.user_id
JOIN activity_detail_logs prev_adl
    ON adl.activity_id = prev_adl.activity_id
   AND adl.exercise_id = prev_adl.exercise_id
   AND prev_adl.set_number = adl.set_number - 1
WHERE
    al.status = 'FINISHED'
    AND adl.set_number > 1
    AND prev_adl.score >= 60;
