import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { DateFormat } from '@lingui/react'
import StripeSubscriptionStatus from './StripeSubscriptionStatus'

const DATE_FORMAT = {
  year: 'numeric',
  month: 'long',
  day: 'numeric'
}

export default function Subscription (props) {
  const { createdAt, renewedAt, stripeStatus } = props

  return (
    <dl>
      <dt><Trans id='js.settings.Billing.Subscription.stripeStatus'>Status</Trans></dt>
      <dd><StripeSubscriptionStatus stripeStatus={stripeStatus} /></dd>
      <dt><Trans id='js.settings.Billing.Subscription.createdAt'>Subscribed</Trans></dt>
      <dd><time dateTime={createdAt}><DateFormat value={createdAt} format={DATE_FORMAT} /></time></dd>
      <dt><Trans id='js.settings.Billing.Subscription.status'>Last Renewed</Trans></dt>
      <dd><time dateTime={renewedAt}><DateFormat value={renewedAt} format={DATE_FORMAT} /></time></dd>
    </dl>
  )
}
Subscription.propTypes = {
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
