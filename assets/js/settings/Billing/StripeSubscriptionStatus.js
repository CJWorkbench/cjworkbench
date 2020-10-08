import React from 'react'
import PropTypes from 'prop-types'
import { t, Trans } from '@lingui/macro'

const StripeStatusMessages = {
  trialing: t('js.settings.Billing.StripeSubscriptionStatus.trialing')`Trialing`,
  active: t('js.settings.Billing.StripeSubscriptionStatus.active')`Active`,
  incomplete: t('js.settings.Billing.StripeSubscriptionStatus.incomplete')`Incomplete`,
  incomplete_expired: t('js.settings.Billing.StripeSubscriptionStatus.incomplete_expired')`Expired`,
  past_due: t('js.settings.Billing.StripeSubscriptionStatus.past_due')`Past due`,
  canceled: t('js.settings.Billing.StripeSubscriptionStatus.canceled')`Canceled`,
  unpaid: t('js.settings.Billing.StripeSubscriptionStatus.canceled')`Unpaid`
}

export default function StripeSubscriptionStatus (props) {
  const { stripeStatus } = props
  return <Trans id={StripeStatusMessages[stripeStatus]} />
}
StripeSubscriptionStatus.propTypes = {
  stripeStatus: PropTypes.oneOf(Object.keys(StripeStatusMessages)).isRequired
}
