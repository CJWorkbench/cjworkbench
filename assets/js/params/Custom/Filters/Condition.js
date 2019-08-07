import React from 'react'
import PropTypes from 'prop-types'
import { ConditionPropType } from './PropTypes'

const ValidConditions = {
  text: [
    { name: 'text_contains', label: 'Text contains' },
    { name: 'text_does_not_contain', label: 'Text does not contain' },
    { name: 'text_is_exactly', label: 'Text is exactly' },
    { name: 'text_is_not_exactly', label: 'Text is not exactly' },
    { name: 'text_contains_regex', label: 'Text contains regex' },
    { name: 'text_does_not_contain_regex', label: 'Text does not contain regex' },
    { name: 'text_is_exactly_regex', label: 'Text matches regex exactly' }
  ],
  datetime: [
    { name: 'date_is', label: 'Date is' },
    { name: 'date_is_not', label: 'Date is not' },
    { name: 'date_is_before', label: 'Date is before' },
    { name: 'date_is_after', label: 'Date is after' }
  ],
  number: [
    { name: 'number_equals', label: 'Number is' },
    { name: 'number_does_not_equal', label: 'Number is not' },
    { name: 'number_is_greater_than', label: 'Number is greater than' },
    { name: 'number_is_greater_than_or_equals', label: 'Number is greater than or equals' },
    { name: 'number_is_less_than', label: 'Number is less than' },
    { name: 'number_is_less_than_or_equals', label: 'Number is less than or equals' }
  ],
  any: [
    { name: 'cell_is_empty', label: 'Cell is null' },
    { name: 'cell_is_not_empty', label: 'Cell is not null' },
    { name: 'cell_is_empty_str_or_null', label: 'Cell is empty' },
    { name: 'cell_is_not_empty_str_or_null', label: 'Cell is not empty' }
  ]
}

export default class Condition extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    value: ConditionPropType.isRequired, // may be ''
    dtype: PropTypes.oneOf(['text', 'datetime', 'number']).isRequired,
    onChange: PropTypes.func.isRequired // func('text_is_exactly' or other) => undefined
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, value, dtype } = this.props
    const options = ValidConditions[dtype].concat(ValidConditions.any)

    return (
      <select
        name={name}
        disabled={isReadOnly}
        value={value}
        onChange={this.onChange}
      >
        <option value=''>Select condition</option>
        {options.map(({ name, label }) => (
          <option key={name} value={name}>{label}</option>
        ))}
      </select>
    )
  }
}
