import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'
import IconText from '../../../icons/text.svg'

function AddTextBlockPrompt ({ onSubmit, i18n }) {
  const handleClick = React.useCallback(() => {
    onSubmit({
      markdown: i18n._(t(/* i18n: When an editor adds a text block to a report, this placeholder text appears */'js.WorkflowEditor.Report.AddTextBlockPrompt.placeholder')`Enter MarkDown text here`)
    })
  }, [onSubmit, i18n])
  return (
    <button
      name='add-text-block'
      onClick={handleClick}
      title={i18n._(t('js.WorkflowEditor.Report.AddTextBlockPrompt.hoverText')`Add Text Block`)}
    >
      <IconText />
    </button>
  )
}
AddTextBlockPrompt.propTypes = {
  onSubmit: PropTypes.func.isRequired // func({ markdown }) => undefined
}
export default withI18n()(AddTextBlockPrompt)
