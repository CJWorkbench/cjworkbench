// Simple wrapper over HTML <select>
import React from 'react'
import PropTypes from 'prop-types'

export default class MenuParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    items: PropTypes.string.isRequired, // like 'Apple|Banana|Kitten'
    selectedIdx: PropTypes.number.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(newIndex) => undefined
  }

  onChange = (ev) => {
    this.props.onChange(+ev.target.value)
  }

  render() {
    const { items, name, isReadOnly, selectedIdx } = this.props

    const itemDivs = items.split('|').map((name, idx) => {
        return (
          <option
            key={idx}
            value={idx}
            className='dropdown-menu-item t-d-gray content-1'
          >
            {name}
          </option>
        )
    })

    return (
        <select
          className='custom-select'
          name={name}
          value={selectedIdx}
          onChange={this.onChange}
          disabled={isReadOnly}
        >
          {itemDivs}
        </select>
    );
  }
}
