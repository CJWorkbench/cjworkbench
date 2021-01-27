import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Main from './Main'
import SidebarNav from './SidebarNav'
import getSettingsPages from './settingsPages'
import Billing from './Billing'
import Navbar from '../Workflows/Navbar'

export default function BillingPage (props) {
  const { api, user } = props

  const createBillingPortalSessionAndRedirect = React.useCallback(async () => {
    const { billingPortalSession } = await api.createStripeBillingPortalSession()
    window.location = billingPortalSession.url
  }, [api])

  return (
    <>
      <Navbar user={user} />
      <Main>
        <SidebarNav pages={getSettingsPages()} activePath='/settings/billing' />
        <div>
          <h1><Trans id='js.settings.BillingPage.title'>Billing</Trans></h1>
          <Billing
            user={user}
            onClickManage={createBillingPortalSessionAndRedirect}
          />
        </div>
      </Main>
    </>
  )
}
BillingPage.propTypes = {
  api: PropTypes.shape({
    createStripeCheckoutSession: PropTypes.func.isRequired,
    createStripeBillingPortalSession: PropTypes.func.isRequired
  }).isRequired,
  user: PropTypes.object.isRequired
}
