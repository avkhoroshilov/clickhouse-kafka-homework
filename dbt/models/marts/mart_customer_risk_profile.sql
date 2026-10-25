with customer_metrics as (
    select
        customer_id,
        min(transaction_time) as first_transaction_at,
        max(transaction_time) as last_transaction_at,
        count() as transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ percentage('countIf(is_fraud = 1)', 'count()') }} as fraud_rate,
        sum(amount) as total_amount,
        coalesce(sumIf(amount, is_fraud = 1), toDecimal128(0, 2)) as fraud_amount,
        avg(toFloat64(amount)) as avg_amount,
        uniqExact(merchant_id) as unique_merchants,
        uniqExact(category) as unique_categories
    from {{ ref('stg_transactions') }}
    group by customer_id
)

select
    *,
    case
        when
            fraud_count >= {{ var('high_risk_min_frauds') }}
            and fraud_rate >= {{ var('high_risk_rate_pct') }} then 'HIGH'
        when fraud_count > 0 then 'MEDIUM'
        else 'LOW'
    end as risk_level
from customer_metrics
