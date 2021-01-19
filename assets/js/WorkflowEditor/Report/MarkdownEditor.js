import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'

export default function MarkdownEditor ({ value, onChange, onSubmit, onCancel }) {
  const handleChange = React.useCallback(ev => onChange(ev.target.value), [onChange])
  const handleSubmit = React.useCallback(ev => {
    ev.preventDefault()
    onSubmit()
  }, [onSubmit])
  const handleReset = React.useCallback(ev => {
    ev.preventDefault()
    onCancel()
  }, [onCancel])
  const handleKeyDown = React.useCallback(ev => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
      ev.preventDefault()
      onSubmit()
    }
  }, [onSubmit])

  return (
    <form
      className='markdown-editor'
      method='post'
      action='#'
      onSubmit={handleSubmit}
      onReset={handleReset}
    >
      <div className='autosize'>
        <div className='invisible-size-setter'>{value}</div>
        <textarea
          autoFocus
          name='markdown'
          placeholder={t({
            id: 'js.WorkflowEditor.Report.MarkdownEditor.placeholder',
            message: 'Enter MarkDown text here',
            comment: 'When an editor adds a text block to a report, this placeholder text appears'
          })}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
        />
      </div>
      <div className='buttons'>
        <button className='action-button button-gray' type='reset'>
          <Trans id='js.WorkflowEditor.Report.MarkdownEditor.cancel'>Cancel</Trans>
        </button>
        <button className='action-button button-blue' type='submit'>
          <Trans id='js.WorkflowEditor.Report.MarkdownEditor.submit'>Save</Trans>
        </button>
      </div>
    </form>
  )
}
MarkdownEditor.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired, // onChange(value) => undefined
  onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
  onCancel: PropTypes.func.isRequired // onCancel() => undefined
}
