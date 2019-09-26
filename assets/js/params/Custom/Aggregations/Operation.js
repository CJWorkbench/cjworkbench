import React from 'react'
import PropTypes from 'prop-types'

export default function Operation ({ isReadOnly, name, value, onChange }) {
  // Mimic <MenuParam>'s HTML, but with string values. As of [2019-01-04],
  // <MenuParam> still only allows integer values, even though _every_ use
  // case warrants strings.
  return (
    <select
      className='operation'
      name={name}
      value={value}
      onChange={onChange}
      readOnly={isReadOnly}
    >
      <option value='size'>Count</option>
      <option value='nunique'>Count unique</option>
      <option value='sum'>Sum</option>
      <option value='mean'>Average (Mean)</option>
      <option value='median'>Median</option>
      <option value='min'>Minimum</option>
      <option value='max'>Maximum</option>
      <option value='first'>First</option>
    </select>
  )
}
Operation.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
  onChange: PropTypes.func.isRequired // func(ev) => undefined
}
