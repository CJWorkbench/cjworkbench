import React from 'react'
import PropTypes from 'prop-types'
import { ComparisonOperatorPropType } from './PropTypes'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const ValidComparisonOperators = {
  text: [
    { name: 'text_contains', label: t('js.params.Condition.Comparison.textContains')`Text contains` },
    { name: 'text_does_not_contain', label: t('js.params.Condition.Comparison.textDoesNotContain')`Text does not contain` },
    { name: 'text_is', label: t('js.params.Condition.Comparison.textIs')`Text is exactly` },
    { name: 'text_is_not', label: t('js.params.Condition.Comparison.textIsNot')`Text is not exactly` }
  ],
  timestamp: [
    { name: 'timestamp_is', label: t('js.params.Condition.Comparison.timestampIs')`Timestamp is` },
    { name: 'timestamp_is_not', label: t('js.params.Condition.Comparison.timestampIsNot')`Timestamp is not` },
    { name: 'timestamp_is_after', label: t('js.params.Condition.Comparison.timestampIsAfter')`Timestamp is after` },
    { name: 'timestamp_is_after_or_equals', label: t('js.params.Condition.Comparison.timestampIsAfterOrEquals')`Timestamp is after or equals` },
    { name: 'timestamp_is_before', label: t('js.params.Condition.Comparison.timestampIsBefore')`Timestamp is before` },
    { name: 'timestamp_is_before_or_equals', label: t('js.params.Condition.Comparison.timestampIsBeforeOrEquals')`Timestamp is before or equals` }
  ],
  number: [
    { name: 'number_is', label: t('js.params.Condition.Comparison.numberIs')`Number is` },
    { name: 'number_is_not', label: t('js.params.Condition.Comparison.numberIsNot')`Number is not` },
    { name: 'number_is_greater_than', label: t('js.params.Condition.Comparison.numberIsGreaterThan')`Number is greater than` },
    { name: 'number_is_greater_than_or_equals', label: t('js.params.Condition.Comparison.numberIsGreaterThanOrEqual')`Number is greater than or equals` },
    { name: 'number_is_less_than', label: t('js.params.Condition.Comparison.numberIsLessThan')`Number is less than` },
    { name: 'number_is_less_than_or_equals', label: t('js.params.Condition.Comparison.numberIsLessThanOrEqual')`Number is less than or equals` }
  ],
  any: [
    { name: 'cell_is_null', label: t('js.params.Condition.Comparison.cellIsNull')`Cell is null` },
    { name: 'cell_is_not_null', label: t('js.params.Condition.Comparison.cellIsNotNull')`Cell is not null` },
    { name: 'cell_is_empty', label: t('js.params.Condition.Comparison.cellIsEmpty')`Cell is empty` },
    { name: 'cell_is_not_empty', label: t('js.params.Condition.Comparison.cellIsNotEmpty')`Cell is not empty` }
  ]
}

export class ComparisonOperator extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    value: ComparisonOperatorPropType.isRequired, // may be ''
    dtype: PropTypes.oneOf(['text', 'timestamp', 'number']).isRequired,
    onChange: PropTypes.func.isRequired // func('text_is_exactly' or other) => undefined
  }

  handleChange = (ev) => {
    this.props.onChange(ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, value, i18n, dtype } = this.props
    const options = ValidComparisonOperators[dtype].concat(ValidComparisonOperators.any)

    return (
      <select
        name={name}
        disabled={isReadOnly}
        value={value}
        onChange={this.handleChange}
      >
        <option value=''>{i18n._(/* i18n: As in 'select a condition relative to which we will filter'. Comparison here is something of the form 'IF something IS like that'. */t('js.params.Condition.Comparison.selectComparison')`Select condition`)}</option>
        {options.map(({ name, label }) => (
          <option key={name} value={name}>{i18n._(label)}</option>
        ))}
      </select>
    )
  }
}

export default withI18n()(ComparisonOperator)
