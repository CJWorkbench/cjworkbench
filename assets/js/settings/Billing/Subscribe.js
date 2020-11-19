import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function Subscribe (props) {
  const { onClick } = props
  const [loading, setLoading] = React.useState(false)
  const handleClick = React.useCallback(async () => {
    setLoading(true)
    try { await onClick() } catch {}
    setLoading(false)
  }, [onClick])

  return (
    <button className='action-button button-blue--fill' onClick={handleClick} disabled={loading}>
      <Trans id='js.settings.Billing.Subscribe.buttonText'>Subscribe</Trans>
    </button>
  )
}
Subscribe.propTypes = {
  onClick: PropTypes.func.isRequired
}
