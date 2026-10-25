select
    us_state,
    count() as transaction_count,
    countIf(is_fraud = 1) as fraud_count,
    {{ percentage('countIf(is_fraud = 1)', 'count()') }} as fraud_rate,
    uniqExact(customer_id) as unique_customers,
    uniqExact(merchant_id) as unique_merchants,
    sum(amount) as total_amount,
    coalesce(sumIf(amount, is_fraud = 1), toDecimal128(0, 2)) as fraud_amount
from {{ ref('stg_transactions') }}
group by us_state
