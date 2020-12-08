import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import IconAddc from '../../../icons/addc.svg'

export default function NewTabPrompt (props) {
  const { create } = props
  return (
    <button
      className='new-tab'
      onClick={create}
      title={t({ id: 'js.WorkflowEditor.Tabs.NewTabPrompt.createTab.title', message: 'Create tab' })}
    >
      <IconAddc />
    </button>
  )
}
NewTabPrompt.propTypes = {
  create: PropTypes.func.isRequired // func() => undefined
}
