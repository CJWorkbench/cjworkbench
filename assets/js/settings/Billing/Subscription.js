import React from 'react'
import PropTypes from 'prop-types'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'
import StripeSubscriptionStatus from './StripeSubscriptionStatus'
import StripeAmount from '../StripeAmount'

const DATE_FORMAT = {
  year: 'numeric',
  month: 'long',
  day: 'numeric'
}

export default function Subscription (props) {
  const { price, createdAt, renewedAt, stripeStatus } = props
  const { product: { name }, amount, currency, interval } = price

  return (
    <div className='subscription'>
      <h3>{name}</h3>
      <h4><StripeAmount amount={amount} currency={currency} interval={interval} /></h4>
      <div className='metadata'>
        <span className='stripe-subscription-status'><StripeSubscriptionStatus stripeStatus={stripeStatus} /></span>
        <span className='stripe-created-at'>
          <Trans id='js.settings.billing.Subscription.createdAt' comment='e.g., "Subscribed January 27, 2021"'>
            Subscribed <time dateTime={createdAt}>{i18n.date(createdAt, DATE_FORMAT)}</time>
          </Trans>
        </span>
        {createdAt !== renewedAt ? (
          <span className='stripe-renewed-at'>
            <Trans id='js.settings.billing.Subscription.renewedAt' comment='e.g., "Renewed February 27, 2021"'>
              Renewed <time dateTime={renewedAt}>{i18n.date(createdAt, DATE_FORMAT)}</time>
            </Trans>
          </span>
        ) : null}
      </div>
    </div>
  )
}
Subscription.propTypes = {
  price: PropTypes.shape({
    product: PropTypes.shape({
      name: PropTypes.string.isRequired
    }).isRequired,
    amount: PropTypes.number.isRequired,
    currency: PropTypes.string.isRequired,
    interval: PropTypes.oneOf(['month', 'year']).isRequired
  }).isRequired,
  createdAt: PropTypes.string.isRequired, // ISO8601 Date
  renewedAt: PropTypes.string.isRequired, // ISO8601 Date
  stripeStatus: PropTypes.oneOf([
    'trialing',
    'active',
    'incomplete',
    'incomplete_expired',
    'past_due',
    'canceled',
    'unpaid'
  ]).isRequired
}
