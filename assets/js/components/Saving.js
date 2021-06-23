import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function Saving (props) {
  const { failed, onClickRetry } = props

  return failed
    ? (
      <div className='saving save-failed'>
        <Trans id='js.components.Saving.failed'>Could not save</Trans>
        <button
          type='button'
          name='retry'
          onClick={onClickRetry}
        >
          <Trans id='js.components.Saving.retry'>Retry</Trans>
        </button>
      </div>
      )
    : (
      <div className='saving'>
        <Trans id='js.components.Saving.saving'>Saving…</Trans>
      </div>
      )
}
Saving.propTypes = {
  failed: PropTypes.bool.isRequired,
  onClickRetry: PropTypes.func.isRequired // func() => undefined
}
