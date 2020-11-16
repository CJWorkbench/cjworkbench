import PropTypes from 'prop-types'

export const ComparisonOperatorPropType = PropTypes.oneOf([
  '',
  'cell_is_empty',
  'cell_is_not_empty',
  'cell_is_null',
  'cell_is_not_null',
  'timestamp_is',
  'timestamp_is_after',
  'timestamp_is_after_or_equals',
  'timestamp_is_before',
  'timestamp_is_before_or_equals',
  'timestamp_is_not',
  'number_is_not',
  'number_is',
  'number_is_greater_than',
  'number_is_greater_than_or_equals',
  'number_is_less_than',
  'number_is_less_than_or_equals',
  'text_contains',
  'text_does_not_contain',
  'text_is',
  'text_is_not'
])

export const ComparisonDefaultProps = {
  operation: '',
  column: '',
  value: '',
  isCaseSensitive: false,
  isRegex: false
}

export const ComparisonPropType = PropTypes.shape({
  operation: ComparisonOperatorPropType.isRequired, // default ''
  column: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired, // default ''
  isCaseSensitive: PropTypes.bool.isRequired, // default false
  isRegex: PropTypes.bool.isRequired // default false
})

export const AndOrPropType = PropTypes.oneOf(['and', 'or'])

export const GroupPropType = PropTypes.shape({
  operation: AndOrPropType.isRequired,
  conditions: PropTypes.arrayOf(ComparisonPropType.isRequired).isRequired
})

export const ConditionPropType = PropTypes.shape({
  operation: AndOrPropType.isRequired,
  conditions: PropTypes.arrayOf(GroupPropType.isRequired).isRequired
})
