import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'

/**
 * Display an amount of money from Stripe, with a currency symbol.
 *
 * Stripe presents some amounts multiplied by 100 and others plain.
 * some values by 100 and not others. This displays the human-legible
 * value, without the Stripe insanity.
 * Stripe ref: https://stripe.com/docs/currencies#zero-decimal
 */
export default function StripeAmount (props) {
  const { currency, value } = props
  const isoCurrency = currency.toUpperCase()
  const ZeroDecimalCurrencies = 'BIF CLP DJF GNF JPY KMF KRW MGA PYG RWF UGX VND VUV XAF XOF XPF'
  const realValue = ZeroDecimalCurrencies.includes(isoCurrency) ? value : value / 100
  return <>{i18n.number(realValue, { style: 'currency', currency: isoCurrency })}</>
}
StripeAmount.propTypes = {
  value: PropTypes.number.isRequired, // integer
  currency: PropTypes.string.isRequired // lowercase 3-char ISO country code
}
