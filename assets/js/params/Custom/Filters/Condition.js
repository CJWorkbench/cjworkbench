import React from 'react'
import PropTypes from 'prop-types'
import { ConditionPropType } from './PropTypes'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const ValidConditions = {
  text: [
    { name: 'text_contains', label: t('condition.textcontainer')`Text contains` },
    { name: 'text_does_not_contain', label: t('condition.textdoesntcontain')`Text does not contain` },
    { name: 'text_is_exactly', label: t('condition.textexactly')`Text is exactly` },
    { name: 'text_is_not_exactly', label: t('condition.textnotexactly')`Text is not exactly` },
    { name: 'text_contains_regex', label: t('condition.textcontainsregex')`Text contains regex` },
    { name: 'text_does_not_contain_regex', label: t('condition.textdoesntcontainregex')`Text does not contain regex` },
    { name: 'text_is_exactly_regex', label: t('condition.Textmatchesregexexactly')`Text matches regex exactly` }
  ],
  datetime: [
    { name: 'date_is', label: t('condition.Dateis')`Date is` },
    { name: 'date_is_not', label: t('condition.Dateisnot')`Date is not` },
    { name: 'date_is_before', label: t('condition.Dateisbefore')`Date is before` },
    { name: 'date_is_after', label: t('condition.Dateisafter')`Date is after` }
  ],
  number: [
    { name: 'number_equals', label: t('condition.Numberis')`Number is` },
    { name: 'number_does_not_equal', label: t('condition.Numberisnot')`Number is not` },
    { name: 'number_is_greater_than', label: t('condition.Numberisgreaterthan')`Number is greater than` },
    { name: 'number_is_greater_than_or_equals', label: t('condition.Numbergreaterthanequals')`Number is greater than or equals` },
    { name: 'number_is_less_than', label: t('condition.Numberislessthan')`Number is less than` },
    { name: 'number_is_less_than_or_equals', label: t('condition.Numberislessthanorequals')`Number is less than or equals` }
  ],
  any: [
    { name: 'cell_is_empty', label: t('condition.Cellisnull')`Cell is null` },
    { name: 'cell_is_not_empty', label: t('condition.Cellisnotnull')`Cell is not null` },
    { name: 'cell_is_empty_str_or_null', label: t('condition.Cellisempty')`Cell is empty` },
    { name: 'cell_is_not_empty_str_or_null', label: t('condition.Cellisnotempty')`Cell is not empty` }
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
        <option value=''> {i18n._(t('workbench.selectcondition')`Select condition`)}</option>
        {options.map(({ name, label }) => (
          <option key={name} value={name}>{i18n._(label)}</option>
        ))}
      </select>
    )
  }
}

export default withI18n()(Condition)
