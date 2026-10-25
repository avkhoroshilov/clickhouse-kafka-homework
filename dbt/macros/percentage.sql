{% macro percentage(numerator, denominator) -%}
    100.0 * ({{ numerator }}) / nullIf({{ denominator }}, 0)
{%- endmacro %}
