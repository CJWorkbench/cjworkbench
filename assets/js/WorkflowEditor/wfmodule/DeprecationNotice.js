import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default function DeprecationMessage ({ helpUrl, message }) {
  if (!message) return null

  return (
    <div className='module-deprecated'>
      <p>{message}</p>
      <a target='_blank' rel='noopener noreferrer' href={helpUrl}>
        <Trans id='js.WorkflowEditor.wfmodule.DeprecationNotice.learnHowToReplace'>Learn how to replace this step</Trans>
      </a>
    </div>
  )
}
DeprecationMessage.propTypes = {
  helpUrl: PropTypes.string.isRequired,
  message: PropTypes.string // null/undefined means "not deprecated"
}
