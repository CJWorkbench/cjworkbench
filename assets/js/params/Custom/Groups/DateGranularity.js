import React from 'react'
import PropTypes from 'prop-types'

export default class DateGranularity extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <select name=...>
    colname: PropTypes.string.isRequired,
    value: PropTypes.oneOf('STHDMQY'.split('')), // or null
    onChange: PropTypes.func.isRequired // func(colname, value) => undefined
  }

  onChange = (ev) => {
    const { colname, onChange } = this.props
    onChange(colname, ev.target.value || null)
  }

  render () {
    const { isReadOnly, name, colname, value } = this.props

    // Mimic <MenuParam>'s HTML, but with string values. As of [2019-01-04],
    // <MenuParam> still only allows integer values, even though _every_ use
    // case warrants strings.

    return (
      <label className='date-granularity'>
        <h5>Granularity of “{colname}”</h5>
        <select
          className='custom-select'
          name={name}
          value={value || ''}
          onChange={this.onChange}
          readOnly={isReadOnly}
        >
          <option value=''>as is</option>
          <option value='S'>by second</option>
          <option value='T'>by minute</option>
          <option value='H'>by hour</option>
          <option value='D'>by day</option>
          <option value='M'>by month</option>
          <option value='Q'>by quarter</option>
          <option value='Y'>by year</option>
        </select>
      </label>
    )
  }
}
