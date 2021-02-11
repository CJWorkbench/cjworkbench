import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function StripeSubscriptionStatus (props) {
  const { stripeStatus } = props
  switch (stripeStatus) {
    case 'trialing':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.trialing'>Trialing</Trans>
    case 'active':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.active'>Active</Trans>
    case 'incomplete':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.incomplete'>Incomplete</Trans>
    case 'incomplete_expired':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.incomplete_expired'>Expired</Trans>
    case 'past_due':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.past_due'>Past due</Trans>
    case 'canceled':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.canceled'>Canceled</Trans>
    case 'unpaid':
      return <Trans id='js.settings.Billing.StripeSubscriptionStatus.unpaid'>Unpaid</Trans>
  }
}
StripeSubscriptionStatus.propTypes = {
  stripeStatus: PropTypes.oneOf([
    'trialing', 'active', 'incomplete', 'incomplete_expired', 'past_due', 'canceled', 'unpaid'
  ]).isRequired
}
