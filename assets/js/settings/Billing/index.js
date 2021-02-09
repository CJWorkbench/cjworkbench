import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import ManageBilling from './ManageBilling'
import Subscription from './Subscription'

export default function Billing (props) {
  const { onClickManage, user: { stripeCustomerId, subscriptions } } = props
  return (
    <section className='billing'>
      <h2><Trans id='js.settings.Billing.subscriptions.title'>Current Subscription</Trans></h2>
      {subscriptions.length ? (
        <ul className='subscriptions'>
          {subscriptions.map(subscription => (
            <li key={subscription.stripeSubscriptionId}>
              <Subscription
                price={subscription.price}
                createdAt={subscription.createdAt}
                renewedAt={subscription.renewedAt}
                stripeStatus={subscription.stripeStatus}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p>
          <Trans id='js.settings.Billing.subscriptions.empty'>
            You are not subscribed. Please <a href='/settings/plan'>upgrade</a>.
          </Trans>
        </p>
      )}
      {stripeCustomerId ? (
        <>
          <h2><Trans id='js.settings.Billing.manage.title'>Manage payments</Trans></h2>
          <p>
            <Trans id='js.settings.Billing.manage.description'>
              You may use Stripe to view invoices, update credit card details or cancel subscriptions.
            </Trans>
          </p>
          <ManageBilling onClick={onClickManage} />
        </>
      ) : null}
    </section>
  )
}
Billing.propTypes = {
  onClickManage: PropTypes.func.isRequired,
  user: PropTypes.shape({
    stripeCustomerId: PropTypes.string, // or null
    subscriptions: PropTypes.arrayOf(
      PropTypes.shape({
        stripeSubscriptionId: PropTypes.string.isRequired,
        createdAt: PropTypes.string.isRequired, // ISO8601 Date
        renewedAt: PropTypes.string.isRequired, // ISO8601 Date
        price: PropTypes.object.isRequired,
        stripeStatus: PropTypes.oneOf([
          'trialing',
          'active',
          'incomplete',
          'incomplete_expired',
          'past_due',
          'canceled',
          'unpaid'
        ]).isRequired
      }).isRequired
    ).isRequired
  }).isRequired
}
