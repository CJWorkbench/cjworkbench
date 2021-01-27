import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function ManageBilling (props) {
  const { onClick } = props
  const [loading, setLoading] = React.useState(false)
  const handleClick = React.useCallback(async () => {
    setLoading(true)
    try { await onClick() } catch {}
    setLoading(false)
  }, [onClick])

  return (
    <button className='manage-billing' onClick={handleClick} disabled={loading}>
      <Trans id='js.settings.Billing.ManageBilling.buttonText'>Manage payments with Stripe</Trans>
    </button>
  )
}
ManageBilling.propTypes = {
  onClick: PropTypes.func.isRequired
}
