import PropTypes from 'prop-types'

export const ConditionPropType = PropTypes.oneOf([
  '',
  'cell_is_empty',
  'cell_is_empty_str_or_null',
  'cell_is_not_empty',
  'cell_is_not_empty_str_or_null',
  'date_is',
  'date_is_after',
  'date_is_before',
  'date_is_not',
  'number_does_not_equal',
  'number_equals',
  'number_is_greater_than',
  'number_is_greater_than_or_equals',
  'number_is_less_than',
  'number_is_less_than_or_equals',
  'text_contains',
  'text_contains_regex',
  'text_does_not_contain',
  'text_does_not_contain_regex',
  'text_is_exactly',
  'text_is_exactly_regex'
])

export const SubfilterPropType = PropTypes.shape({
  colname: PropTypes.string.isRequired,
  condition: ConditionPropType.isRequired, // default ''
  value: PropTypes.string.isRequired, // default ''
  case_sensitive: PropTypes.bool.isRequired // default false
})

export const OperatorPropType = PropTypes.oneOf(['and', 'or'])

export const FilterPropType = PropTypes.shape({
  operator: OperatorPropType.isRequired,
  subfilters: PropTypes.arrayOf(SubfilterPropType.isRequired).isRequired
})

export const FiltersPropType = PropTypes.shape({
  operator: OperatorPropType.isRequired,
  filters: PropTypes.arrayOf(FilterPropType.isRequired).isRequired
})
