import React from 'react'
import PropTypes from 'prop-types'
import Menu from './Menu'

/**
 * A control that helps the user author a number format.
 *
 * Its `value` is a string such as "" ('default') or "${:,.2f}" (a Python
 * format string, guaranteed to have a single `{:...}` in it.
 */
export default function NumberFormat (props) {
  // TODO implement something legit. For now we just offer a few common options.
  const enumOptions = [
    { label: 'Decimal, fixed precision: 1,500.00', value: '{:,.2f}' },
    { label: 'Integer: 1,500', value: '{:,d}' },
    { label: 'Decimal: 1,500.0012', value: '{:,}' },
    { label: 'Integer, no commas: 1500', value: '{:d}' },
    { label: 'Decimal, no commas: 1500.0012', value: '{:}' },
    'separator',
    { label: 'Currency: $1,500.00', value: '${:,.2f}' },
    { label: 'Percentage: 15.0%', value: '{:,.1%}' }
  ]

  return (
    <Menu
      {...props}
      enumOptions={enumOptions}
    />
  )
}
