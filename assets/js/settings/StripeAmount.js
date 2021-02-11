import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'

/**
 * Display an amount of money from Stripe, with a currency symbol.
 *
 * Stripe presents some amounts multiplied by 100 and others plain.
 * some values by 100 and not others. This displays the human-legible
 * value, without the Stripe insanity.
 * Stripe ref: https://stripe.com/docs/currencies#zero-decimal
 */
export default function StripeAmount (props) {
  const { currency, amount, interval } = props
  const isoCurrency = currency.toUpperCase()
  const ZeroDecimalCurrencies = 'BIF CLP DJF GNF JPY KMF KRW MGA PYG RWF UGX VND VUV XAF XOF XPF'
  const value = ZeroDecimalCurrencies.includes(isoCurrency) ? amount : amount / 100

  const price = i18n.number(value, { style: 'currency', currency: isoCurrency })

  switch (interval) {
    case 'year':
      return <Trans id='js.settings.Plan.PlanTable.amount.perMonth'><strong>{price}</strong>/year</Trans>
    default:
      return <Trans id='js.settings.Plan.PlanTable.amount.perYear'><strong>{price}</strong>/month</Trans>
  }
}
StripeAmount.propTypes = {
  amount: PropTypes.number.isRequired, // integer
  currency: PropTypes.string.isRequired, // lowercase 3-char ISO country code
  interval: PropTypes.oneOf(['month', 'year']).isRequired
}
