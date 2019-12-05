/* eslint no-template-curly-in-string: 0 */
import React from 'react'
import Menu from './Menu'
import { withI18n } from '@lingui/react'
import { t } from '@lingui/macro'
import { hideFromTrans } from '../i18n/messages'

/**
 * A control that helps the user author a number format.
 *
 * Its `value` is a string such as "" ('default') or "${:,.2f}" (a Python
 * format string, guaranteed to have a single `{:...}` in it.
 */
function NumberFormat ({ i18n, ...props }) {
  // TODO implement something legit. For now we just offer a few common options.
  const enumOptions = [
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.decimal.fixed')`Decimal, fixed precision: ${hideFromTrans('1,500.00')}`
      ),
      value: '{:,.2f}'
    },
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.decimal.default')`Decimal: ${hideFromTrans('1,500.0012')}`
      ),
      value: '{:,}'
    },
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.decimal.noCommas')`Decimal, no commas: ${hideFromTrans('1500.0012')}`
      ),
      value: '{:}'
    },
    'separator',
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.integer.default')`Integer: ${hideFromTrans('1,500')}`
      ),
      value: '{:,d}'
    },
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.integer.noCommas')`Integer, no commas: ${hideFromTrans('1500')}`
      ),
      value: '{:d}'
    },
    'separator',
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.currency')`Currency: ${hideFromTrans('$1,500.00')}`
      ),
      value: '${:,.2f}'
    },
    {
      label: i18n._(
        /* i18n: The parameter contains an example */
        t('js.params.NumberFormat.percentage')`Percentage: ${hideFromTrans('15.0%')}`
      ),
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

export default withI18n()(NumberFormat)
