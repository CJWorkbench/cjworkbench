import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

export default class MenuParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    enumOptions: PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.oneOf(['separator']),
        PropTypes.shape({
          value: PropTypes.any.isRequired,
          label: PropTypes.string.isRequired
        }).isRequired
      ]).isRequired
    ).isRequired,
    value: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired // onChange(newIndex) => undefined
  }

  handleChange = (ev) => {
    this.props.onChange(ev.target.value)
  }

  render () {
    const { name, fieldId, label, enumOptions, isReadOnly, value } = this.props

    const options = enumOptions.map((option, i) => {
      if (option === 'separator') {
        return <option disabled key={i} className='separator' />
      } else {
        // <option> value must always be String
        return <option key={option.value} value={String(option.value)}>{option.label}</option>
      }
    })

    return (
      <>
        <MaybeLabel fieldId={fieldId} label={label} />
        <select
          name={name}
          id={fieldId}
          value={value}
          onChange={this.handleChange}
          disabled={isReadOnly}
        >
          {options}
        </select>
      </>
    )
  }
}
