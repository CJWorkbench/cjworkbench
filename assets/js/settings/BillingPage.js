import { useCallback } from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { Page, MainNav } from '../Page'
import Billing from './Billing'

export default function BillingPage (props) {
  const { api, user } = props

  const createBillingPortalSessionAndRedirect = useCallback(async () => {
    const {
      billingPortalSession
    } = await api.createStripeBillingPortalSession()
    window.location = billingPortalSession.url
  }, [api])

  return (
    <Page>
      <MainNav user={user} currentPath='/settings/billing' />
      <main>
        <header>
          <h1>
            <Trans id='js.settings.BillingPage.title'>Billing</Trans>
          </h1>
        </header>
        <Billing
          user={user}
          onClickManage={createBillingPortalSessionAndRedirect}
        />
      </main>
    </Page>
  )
}
BillingPage.propTypes = {
  api: PropTypes.shape({
    createStripeCheckoutSession: PropTypes.func.isRequired,
    createStripeBillingPortalSession: PropTypes.func.isRequired
  }).isRequired,
  user: PropTypes.object.isRequired
}
