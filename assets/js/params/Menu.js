import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

export default class MenuParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    items: PropTypes.string.isRequired, // like 'Apple|Banana|Kitten'
    value: PropTypes.number.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    this.props.onChange(+ev.target.value)
  }

  render() {
    const { items, name, fieldId, label, isReadOnly, value } = this.props

    const options = items.split('|').map((name, idx) => (
      <option key={idx} value={idx}>{name}</option>
    ))

    return (
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <select
          name={name}
          id={fieldId}
          value={value}
          onChange={this.onChange}
          disabled={isReadOnly}
        >
          {options}
        </select>
      </React.Fragment>
    )
  }
}
