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
    { label: 'Decimal: 1,234.5678', value: '{:,g}' },
    { label: 'Decimal (fixed precision): 1,234.57', value: '{:,.2f}' },
    { label: 'Decimal (no commas): 1234.5678', value: '{:g}' },
    { label: 'Integer: 1,235', value: '{:,d}' },
    { label: 'Integer (no commas): 1235', value: '{:d}' },
    { label: 'Currency: $1,234.57', value: '${:,.2f}' },
    { label: 'Percentage: 123,456.7%', value: '{:,.1%}' }
  ]

  return (
    <Menu
      {...props}
      enumOptions={enumOptions}
    />
  )
}
