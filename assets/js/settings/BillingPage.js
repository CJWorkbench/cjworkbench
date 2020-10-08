import React from 'react'
import PropTypes from 'prop-types'
import { loadStripe } from '@stripe/stripe-js'
import Billing from './Billing'

export default function BillingPage (props) {
  const { api, user } = props

  const createCheckoutSessionAndRedirect = React.useCallback(async () => {
    const { checkoutSession, apiKey } = await api.createStripeCheckoutSession()
    const stripe = await loadStripe(apiKey)
    const result = await stripe.redirectToCheckout({ sessionId: checkoutSession.id })
    if (result.error) {
      console.error(result.error)
    }
  }, [api])

  const createBillingPortalSessionAndRedirect = React.useCallback(async () => {
    const { billingPortalSession } = await api.createStripeBillingPortalSession()
    window.location = billingPortalSession.url
  }, [api])

  return (
    <Billing
      user={user}
      onClickCheckout={createCheckoutSessionAndRedirect}
      onClickManage={createBillingPortalSessionAndRedirect}
    />
  )
}
BillingPage.propTypes = {
  api: PropTypes.shape({
    createStripeCheckoutSession: PropTypes.func.isRequired,
    createStripeBillingPortalSession: PropTypes.func.isRequired
  }).isRequired,
  user: PropTypes.object.isRequired
}
