select
    transaction_date,
    us_state,
    count() as transaction_count,
    sum(amount) as total_amount,
    avg(toFloat64(amount)) as avg_amount,
    quantileExact(0.95) (toFloat64(amount)) as p95_amount,
    countIf(amount_bucket = 'LARGE') as large_transaction_count,
    {{ percentage("countIf(amount_bucket = 'LARGE')", 'count()') }} as large_transaction_share_pct
from {{ ref('stg_transactions') }}
group by transaction_date, us_state
