with cleaned as (
    select
        source_row,
        source_file,
        parseDateTimeBestEffortOrNull(toString(transaction_time), 'UTC') as transaction_time,
        trimBoth(merch) as merchant_name,
        lowerUTF8(trimBoth(cat_id)) as category,
        toDecimal64OrNull(toString(amount), 2) as amount,
        trimBoth(name_1) as first_name,
        trimBoth(name_2) as last_name,
        upperUTF8(trimBoth(gender)) as gender,
        trimBoth(street) as street,
        trimBoth(one_city) as city,
        upperUTF8(trimBoth(us_state)) as us_state,
        trimBoth(post_code) as post_code,
        toFloat64OrNull(toString(lat)) as latitude,
        toFloat64OrNull(toString(lon)) as longitude,
        toUInt64OrNull(toString(population_city)) as city_population,
        trimBoth(jobs) as job,
        toFloat64OrNull(toString(merchant_lat)) as merchant_latitude,
        toFloat64OrNull(toString(merchant_lon)) as merchant_longitude,
        toUInt8OrNull(toString(target)) as is_fraud
    from {{ source('raw', 'transactions') }}
    where source_file = {{ dbt.string_literal(var('train_source_file')) }}
)

select
    {{ dbt_utils.generate_surrogate_key(['source_file', 'source_row']) }} as transaction_id,
    {{ dbt_utils.generate_surrogate_key([
        'lowerUTF8(first_name)', 'lowerUTF8(last_name)', 'lowerUTF8(street)',
        'lowerUTF8(city)', 'us_state', 'post_code'
    ]) }} as customer_id,
    {{ dbt_utils.generate_surrogate_key(['lowerUTF8(merchant_name)']) }} as merchant_id,
    transaction_time,
    toDate(transaction_time) as transaction_date,
    toHour(transaction_time) as transaction_hour,
    {{ dbt_date.day_of_week('transaction_time', isoweek=true) }} as day_of_week,
    merchant_name,
    category,
    amount,
    {{ amount_bucket('amount') }} as amount_bucket,
    first_name,
    last_name,
    gender,
    street,
    city,
    us_state,
    post_code,
    latitude,
    longitude,
    city_population,
    job,
    merchant_latitude,
    merchant_longitude,
    is_fraud,
    source_row,
    source_file
from cleaned
