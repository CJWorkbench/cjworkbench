import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import ManageBilling from './ManageBilling'
import Subscribe from './Subscribe'
import Subscription from './Subscription'

export default function Billing (props) {
  const { onClickCheckout, onClickManage, user: { stripeCustomerId, subscriptions } } = props
  return (
    <section className='billing'>
      <h1><Trans id='js.settings.Billing.h1'>Subscriptions</Trans></h1>
      {subscriptions.length ? (
        <ul className='subscriptions'>
          {subscriptions.map(subscription => (
            <li key={subscription.stripeSubscriptionId}>
              <Subscription
                createdAt={subscription.createdAt}
                renewedAt={subscription.renewedAt}
                stripeStatus={subscription.stripeStatus}
              />
            </li>
          ))}
        </ul>
      ) : null}
      <div className='manage-billing'>
        {subscriptions.length === 0 ? (
          <Subscribe stripeCustomerId={stripeCustomerId} onClick={onClickCheckout} />
        ) : null}
        {stripeCustomerId ? (
          <ManageBilling onClick={onClickManage} />
        ) : null}
      </div>
    </section>
  )
}
Billing.propTypes = {
  onClickCheckout: PropTypes.func.isRequired,
  onClickManage: PropTypes.func.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string, // or null
    subscriptions: PropTypes.arrayOf(PropTypes.shape({
      stripeSubscriptionId: PropTypes.string.isRequired,
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
    }).isRequired).isRequired
  }).isRequired
}
