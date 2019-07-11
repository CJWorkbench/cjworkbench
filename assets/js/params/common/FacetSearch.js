import React from 'react'
import PropTypes from 'prop-types'

/**
 * A search input box.
 *
 * Calls onChange() when the user enters a new value and onReset() when the
 * user presses Escape. The caller is expected to manage the `value` of the
 * search input.
 */
export default function FacetSearch ({ onChange, onReset, value }) {
  const onKeyDown = React.useCallback(ev => {
    switch (ev.key) {
      case 'Escape':
        return onReset()
      case 'Enter':
        ev.preventDefault() // prevent form submit
    }
  })
  const onChangeCallback = React.useCallback(ev => onChange(ev.target.value))

  return (
    <fieldset className='facet-search' onReset={onReset}>
      <input
        type='search'
        placeholder='Search facets...'
        autoComplete='off'
        value={value}
        onChange={onChangeCallback}
        onKeyDown={onKeyDown}
      />
      <button
        type='button'
        onClick={onReset}
        className='close'
        title='Clear Search'
      >
        <i className='icon-close' />
      </button>
    </fieldset>
  )
}
FacetSearch.propTypes = {
  onReset: PropTypes.func.isRequired, // func() => undefined
  onChange: PropTypes.func.isRequired, // func(value) => undefined
  value: PropTypes.string.isRequired // current input
}
