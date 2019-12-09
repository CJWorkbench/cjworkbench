import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const Search = React.memo(function Search ({ i18n, value, onChange }) {
  const handleReset = React.useCallback(() => onChange(''))
  const handleSubmit = React.useCallback(ev => { ev.preventDefault(); ev.stopPropagation() })
  const handleChange = React.useCallback(ev => onChange(ev.target.value))

  return (
    <form className='search' onSubmit={handleSubmit} onReset={handleReset}>

      <input
        type='search'
        placeholder={i18n._(t('js.WorkflowEditor.AddData.Search.placeholder')`Search…`)}
        name='moduleQ'
        autoFocus
        autoComplete='off'
        onChange={handleChange}
        value={value}
      />

      <button type='reset' className='reset' title={i18n._(t('js.WorkflowEditor.AddData.Search.clearButton.hoverText')`Clear Search`)}><i className='icon-close' /></button>
    </form>
  )
})
Search.propTypes = {
  value: PropTypes.string.isRequired, // may be empty
  onChange: PropTypes.func.isRequired // func(value) => undefined
}
export default withI18n()(Search)
