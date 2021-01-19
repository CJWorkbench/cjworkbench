import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import IconText from '../../../icons/text.svg'

export default function AddTextBlockPrompt ({ active, onClick }) {
  return (
    <button
      type='button'
      name='add-text-block'
      className={active ? 'active' : null}
      onClick={onClick}
      title={t({
        id: 'js.WorkflowEditor.Report.AddTextBlockPrompt.hoverText',
        message: 'Add Text Block'
      })}
    >
      <IconText />
    </button>
  )
}
AddTextBlockPrompt.propTypes = {
  active: PropTypes.bool.isRequired,
  onClick: PropTypes.func.isRequired // func() => undefined
}
