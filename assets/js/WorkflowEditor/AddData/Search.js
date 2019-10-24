import React from 'react'
import PropTypes from 'prop-types'
import { I18n } from '@lingui/react'
import { t } from '@lingui/macro'

const Search = React.memo(function Search ({ value, onChange }) {
  const handleReset = React.useCallback(() => onChange(''))
  const handleSubmit = React.useCallback(ev => { ev.preventDefault(); ev.stopPropagation() })
  const handleChange = React.useCallback(ev => onChange(ev.target.value))

  return (
    <form className='search' onSubmit={handleSubmit} onReset={handleReset}>
      <I18n>
        {({ i18n }) => (
          <input
            type='search'
            placeholder={i18n._(t('workflow.searchattribute')`Search…`)}
            name='moduleQ'
            autoFocus
            autoComplete='off'
            onChange={handleChange}
            value={value}
          />
        )}
      </I18n>
      <I18n>
        {({ i18n }) => (
          <button type='reset' className='reset' title={i18n._(t('workflow.clearSearch')`Clear Search`)}><i className='icon-close' /></button>
        )}
      </I18n>
    </form>
  )
})
Search.propTypes = {
  value: PropTypes.string.isRequired, // may be empty
  onChange: PropTypes.func.isRequired // func(value) => undefined
}
export default Search
