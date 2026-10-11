-- Контрольный запрос по исходным строкам с тем же правилом равенства.
SELECT
    us_state,
    tupleElement(winner, 1) AS cat_id,
    tupleElement(winner, 2) AS max_amount,
    tupleElement(winner, 3) AS source_file,
    tupleElement(winner, 4) AS source_row
FROM
(
    SELECT
        toString(us_state) AS us_state,
        argMax(
            tuple(toString(cat_id), amount, toString(source_file), source_row),
            tuple(amount, toString(cat_id), toString(source_file), source_row)
        ) AS winner
    FROM homework.transactions
    GROUP BY us_state
)
ORDER BY us_state
FORMAT CSVWithNames;
