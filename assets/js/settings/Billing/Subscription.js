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
  const { plan, createdAt, renewedAt, stripeStatus } = props
  const { name, amount, currency } = plan

  return (
    <div className='subscription'>
      <h3>{name}</h3>
      <h4>
        <Trans id='js.settings.billing.Subscription.amount' comment='e.g., "$8/month"'>
          <StripeAmount value={amount} currency={currency} />/month
        </Trans>
      </h4>
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
  plan: PropTypes.shape({
    name: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    currency: PropTypes.string.isRequired
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
