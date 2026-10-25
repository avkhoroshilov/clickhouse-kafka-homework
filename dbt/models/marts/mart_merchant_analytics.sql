with merchant_metrics as (
    select
        merchant_id,
        min(merchant_name) as merchant_name,
        count() as transaction_count,
        countIf(is_fraud = 1) as fraud_count,
        {{ percentage('countIf(is_fraud = 1)', 'count()') }} as fraud_rate,
        sum(amount) as total_amount,
        coalesce(sumIf(amount, is_fraud = 1), toDecimal128(0, 2)) as fraud_amount,
        avg(toFloat64(amount)) as avg_amount,
        uniqExact(customer_id) as unique_customers,
        uniqExact(category) as unique_categories
    from {{ ref('stg_transactions') }}
    group by merchant_id
)

select
    *,
    toUInt8(
        transaction_count >= {{ var('merchant_min_transactions') }}
        and fraud_rate >= {{ var('merchant_risk_rate_pct') }}
    ) as is_suspicious
from merchant_metrics
