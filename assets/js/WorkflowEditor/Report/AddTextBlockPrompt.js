import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import IconText from '../../../icons/text.svg'

export default function AddTextBlockPrompt ({ onSubmit }) {
  const handleClick = React.useCallback(() => {
    onSubmit({
      markdown: t({
        id: 'js.WorkflowEditor.Report.AddTextBlockPrompt.placeholder',
        comment: 'When an editor adds a text block to a report, this placeholder text appears',
        message: 'Enter MarkDown text here'
      })
    })
  }, [onSubmit])
  return (
    <button
      name='add-text-block'
      onClick={handleClick}
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
  onSubmit: PropTypes.func.isRequired // func({ markdown }) => undefined
}
