import React from 'react'
import PropTypes from 'prop-types'
import { ConditionPropType } from './PropTypes'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const ValidConditions = {
  text: [
    { name: 'text_contains', label: t('js.params.Custom.Filters.Condition.textContains')`Text contains` },
    { name: 'text_does_not_contain', label: t('js.params.Custom.Filters.Condition.textDoesNotContain')`Text does not contain` },
    { name: 'text_is_exactly', label: t('js.params.Custom.Filters.Condition.textIsExactly')`Text is exactly` },
    { name: 'text_is_not_exactly', label: t('js.params.Custom.Filters.Condition.textIsNotExactly')`Text is not exactly` },
    { name: 'text_contains_regex', label: t('js.params.Custom.Filters.Condition.textContainsRegex')`Text contains regex` },
    { name: 'text_does_not_contain_regex', label: t('js.params.Custom.Filters.Condition.textDoesntContainRegex')`Text does not contain regex` },
    { name: 'text_is_exactly_regex', label: t('js.params.Custom.Filters.Condition.textMatchesRegexExactly')`Text matches regex exactly` }
  ],
  datetime: [
    { name: 'date_is', label: t('js.params.Custom.Filters.Condition.dateIs')`Date is` },
    { name: 'date_is_not', label: t('js.params.Custom.Filters.Condition.dateIsNot')`Date is not` },
    { name: 'date_is_before', label: t('js.params.Custom.Filters.Condition.dateIsBefore')`Date is before` },
    { name: 'date_is_after', label: t('js.params.Custom.Filters.Condition.dateIsAfter')`Date is after` }
  ],
  number: [
    { name: 'number_equals', label: t('js.params.Custom.Filters.Condition.numberIs')`Number is` },
    { name: 'number_does_not_equal', label: t('js.params.Custom.Filters.Condition.numberIsNot')`Number is not` },
    { name: 'number_is_greater_than', label: t('js.params.Custom.Filters.Condition.numberIsGreaterThan')`Number is greater than` },
    { name: 'number_is_greater_than_or_equals', label: t('js.params.Custom.Filters.Condition.NumberIsGreaterOrEqual')`Number is greater than or equals` },
    { name: 'number_is_less_than', label: t('js.params.Custom.Filters.Condition.numberIsLessthan')`Number is less than` },
    { name: 'number_is_less_than_or_equals', label: t('js.params.Custom.Filters.Condition.numberIsLessOrequal')`Number is less than or equals` }
  ],
  any: [
    { name: 'cell_is_empty', label: t('js.params.Custom.Filters.Condition.cellIsnull')`Cell is null` },
    { name: 'cell_is_not_empty', label: t('js.params.Custom.Filters.Condition.cellIsNotnull')`Cell is not null` },
    { name: 'cell_is_empty_str_or_null', label: t('js.params.Custom.Filters.Condition.cellIsempty')`Cell is empty` },
    { name: 'cell_is_not_empty_str_or_null', label: t('js.params.Custom.Filters.Condition.cellIsnotEmpty')`Cell is not empty` }
  ]
}

export class Condition extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    value: ConditionPropType.isRequired, // may be ''
    dtype: PropTypes.oneOf(['text', 'datetime', 'number']).isRequired,
    onChange: PropTypes.func.isRequired // func('text_is_exactly' or other) => undefined
  }

  handleChange = (ev) => {
    this.props.onChange(ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, value, i18n, dtype } = this.props
    const options = ValidConditions[dtype].concat(ValidConditions.any)

    return (
      <select
        name={name}
        disabled={isReadOnly}
        value={value}
        onChange={this.handleChange}
      >
        <option value=''> {i18n._(t('js.params.Custom.Filters.Condition.selectCondition')`Select condition`)}</option>
        {options.map(({ name, label }) => (
          <option key={name} value={name}>{i18n._(label)}</option>
        ))}
      </select>
    )
  }
}

export default withI18n()(Condition)
