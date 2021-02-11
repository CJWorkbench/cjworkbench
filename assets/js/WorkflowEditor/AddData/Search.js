import { memo, useCallback } from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'

const Search = memo(function Search ({ value, onChange }) {
  const handleReset = useCallback(() => onChange(''))
  const handleSubmit = useCallback(ev => {
    ev.preventDefault()
    ev.stopPropagation()
  })
  const handleChange = useCallback(ev => onChange(ev.target.value))

  return (
    <form className='search' onSubmit={handleSubmit} onReset={handleReset}>
      <input
        type='search'
        placeholder={t({
          id: 'js.WorkflowEditor.AddData.Search.placeholder',
          message: 'Search…'
        })}
        name='moduleQ'
        autoFocus
        autoComplete='off'
        onChange={handleChange}
        value={value}
      />
      <button
        type='reset'
        className='reset'
        title={t({
          id: 'js.WorkflowEditor.AddData.Search.clearButton.hoverText',
          message: 'Clear Search'
        })}
      >
        <i className='icon-close' />
      </button>
    </form>
  )
})
Search.propTypes = {
  value: PropTypes.string.isRequired, // may be empty
  onChange: PropTypes.func.isRequired // func(value) => undefined
}

export default Search
