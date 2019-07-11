import React from 'react'
import PropTypes from 'prop-types'

const Search = React.memo(function Search ({ value, onChange }) {
  const handleReset = React.useCallback(() => onChange(''))
  const handleSubmit = React.useCallback(ev => { ev.preventDefault(); ev.stopPropagation() })
  const handleChange = React.useCallback(ev => onChange(ev.target.value))

  return (
    <form className='search' onSubmit={handleSubmit} onReset={handleReset}>
      <input
        type='search'
        placeholder='Search…'
        name='moduleQ'
        autoFocus
        autoComplete='off'
        onChange={handleChange}
        value={value}
      />
      <button type='reset' className='reset' title='Clear Search'><i className='icon-close' /></button>
    </form>
  )
})
Search.propTypes = {
  value: PropTypes.string.isRequired, // may be empty
  onChange: PropTypes.func.isRequired // func(value) => undefined
}
export default Search
