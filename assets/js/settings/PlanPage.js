import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { loadStripe } from '@stripe/stripe-js'
import Main from './Main'
import SidebarNav from './SidebarNav'
import getSettingsPages from './settingsPages'
import Navbar from '../Workflows/Navbar'
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
    <>
      <Navbar user={user} />
      <Main>
        <SidebarNav pages={getSettingsPages()} activePath='/settings/plan' />
        <div>
          <h1><Trans id='js.settings.PlanPage.title'>Plan</Trans></h1>
          <PlanTable
            plans={plans}
            onClickSubscribe={handleClickSubscribe}
            activePlanIds={user.subscribedPlans.map(p => p.stripePriceId)}
          />
        </div>
      </Main>
    </>
  )
}
PlanPage.propTypes = {
  api: PropTypes.shape({
    createStripeCheckoutSession: PropTypes.func.isRequired
  }).isRequired,
  user: PropTypes.object.isRequired,
  plans: PropTypes.array.isRequired
}
