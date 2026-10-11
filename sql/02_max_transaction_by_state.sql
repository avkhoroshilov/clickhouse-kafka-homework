-- Максимальная отдельная транзакция по каждому штату.
-- При равной сумме выбирается лексикографически большая cat_id,
-- затем source_file, затем больший source_row.
-- Merge объединяет состояния даже до фоновых слияний.
SELECT
    us_state,
    tupleElement(winner, 1) AS cat_id,
    tupleElement(winner, 2) AS max_amount,
    tupleElement(winner, 3) AS source_file,
    tupleElement(winner, 4) AS source_row
FROM
(
    SELECT us_state, argMaxMerge(winner) AS winner
    FROM homework.state_max
    GROUP BY us_state
)
ORDER BY us_state
FORMAT CSVWithNames;
