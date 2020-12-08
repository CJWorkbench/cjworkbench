/* eslint no-template-curly-in-string: 0 */
import React from 'react'
import Menu from './Menu'
import { t } from '@lingui/macro'

/**
 * A control that helps the user author a number format.
 *
 * Its `value` is a string such as "" ('default') or "${:,.2f}" (a Python
 * format string, guaranteed to have a single `{:...}` in it.
 */
export default function NumberFormat ({ i18n, ...props }) {
  // TODO implement something legit. For now we just offer a few common options.
  const enumOptions = [
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.decimal.fixed',
        message: 'Decimal, fixed precision: {0}',
        values: { 0: '1,500.00' }
      }),
      value: '{:,.2f}'
    },
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.decimal.default',
        message: 'Decimal: {0}',
        values: { 0: '1,500.0012' }
      }),
      value: '{:,}'
    },
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.decimal.noCommas',
        message: 'Decimal, no commas: {0}',
        values: { 0: '1500.0012' }
      }),
      value: '{:}'
    },
    'separator',
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.integer.default',
        message: 'Integer: {0}',
        values: { 0: '1,500' }
      }),
      value: '{:,d}'
    },
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.integer.noCommas',
        message: 'Integer, no commas: {0}',
        values: { 0: '1500' }
      }),
      value: '{:d}'
    },
    'separator',
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.currency',
        message: 'Currency: {0}',
        values: { 0: '$1,500.00' }
      }),
      value: '${:,.2f}'
    },
    {
      label: t({
        comment: 'The parameter {0} contains an example',
        id: 'js.params.NumberFormat.percentage',
        message: 'Percentage: {0}',
        values: { 0: '15.0%' }
      }),
      value: '{:,.1%}'
    }
  ]

  return (
    <Menu
      {...props}
      enumOptions={enumOptions}
    />
  )
}
