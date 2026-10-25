{% macro amount_bucket(column_name) -%}
    case
        when {{ column_name }} is null then 'UNKNOWN'
        when {{ column_name }} < {{ var('small_amount_threshold') }} then 'SMALL'
        when {{ column_name }} < {{ var('large_amount_threshold') }} then 'MEDIUM'
        else 'LARGE'
    end
{%- endmacro %}
