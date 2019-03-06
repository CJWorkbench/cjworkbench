import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from './util'

export default class MenuParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    items: PropTypes.string, // like 'Apple|Banana|Kitten' -- DEPRECATED
    enumOptions: PropTypes.arrayOf(
      PropTypes.oneOfType([
        PropTypes.oneOf([ 'separator' ]),
        PropTypes.shape({
          value: PropTypes.any.isRequired,
          label: PropTypes.string.isRequired
        }).isRequired
      ]).isRequired
    ), // new-style menu -- once we nix "items" ("menu_items" in spec), add .isRequired here
    value: PropTypes.oneOfType([
      PropTypes.number.isRequired, // DEPRECATED
      PropTypes.string.isRequired // new-style menu
    ]).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    const { items, onChange } = this.props

    // If "items" is set, this is a "deprecated_menu": values are integers.
    const value = items ? +ev.target.value : ev.target.value
    onChange(value)
  }

  get enumOptions () {
    const { items, enumOptions } = this.props

    if (items) {
      return items.split('|').map((label, value) => { // value is the index
        if (!label) return 'separator' // empty string is a separator
        return { label, value }
      })
    } else {
      return enumOptions
    }
  }

  render() {
    const { items, name, fieldId, label, isReadOnly, value } = this.props

    const options = this.enumOptions.map((option, i) => {
      if (option === 'separator') {
        return <option disabled key={i} className='separator' />
      } else {
        return <option key={option.value} value={option.value}>{option.label}</option>
      }
    })

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
