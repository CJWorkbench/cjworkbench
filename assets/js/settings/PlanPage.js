import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { loadStripe } from '@stripe/stripe-js'
import { Page, MainNav } from '../Page'
import PlanTable from './Plan/PlanTable'

export default function PlanPage (props) {
  const { api, user, plans } = props

  const handleClickSubscribe = React.useCallback(async () => {
    const { checkoutSession, apiKey } = await api.createStripeCheckoutSession()
    const stripe = await loadStripe(apiKey)
    const result = await stripe.redirectToCheckout({ sessionId: checkoutSession.id })
    if (result.error) {
      console.error(result.error)
    }
  }, [api])

  return (
    <Page>
      <MainNav user={user} currentPath='/settings/plan' />
      <main>
        <header>
          <h1><Trans id='js.settings.PlanPage.title'>Plan</Trans></h1>
        </header>
        <PlanTable
          plans={plans}
          onClickSubscribe={handleClickSubscribe}
          activePlanIds={user.subscribedPlans.map(p => p.stripePriceId)}
        />
      </main>
    </Page>
  )
}
PlanPage.propTypes = {
  api: PropTypes.shape({
    createStripeCheckoutSession: PropTypes.func.isRequired
  }).isRequired,
  user: PropTypes.object.isRequired,
  plans: PropTypes.array.isRequired
}
