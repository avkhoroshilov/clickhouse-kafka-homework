with hourly_metrics as (
    select
        day_of_week,
        transaction_hour,
        count() as transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ percentage('countIf(is_fraud = 1)', 'count()') }} as fraud_rate,
        sum(amount) as total_amount,
        coalesce(sumIf(amount, is_fraud = 1), toDecimal128(0, 2)) as fraud_amount
    from {{ ref('stg_transactions') }}
    group by day_of_week, transaction_hour
),

baseline as (
    select
        {{ percentage('sum(fraud_count)', 'sum(transaction_count)') }} as overall_fraud_rate
    from hourly_metrics
)

select
    hourly_metrics.*,
    baseline.overall_fraud_rate,
    hourly_metrics.fraud_rate / nullIf(baseline.overall_fraud_rate, 0) as risk_lift,
    toUInt8(
        hourly_metrics.transaction_count >= {{ var('hourly_min_transactions') }}
        and baseline.overall_fraud_rate > 0
        and hourly_metrics.fraud_rate
        >= baseline.overall_fraud_rate * {{ var('hourly_risk_multiplier') }}
    ) as is_high_risk_window
from hourly_metrics
cross join baseline
