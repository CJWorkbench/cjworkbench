import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

/**
 * A search input box.
 *
 * Calls onChange() when the user enters a new value and onReset() when the
 * user presses Escape. The caller is expected to manage the `value` of the
 * search input.
 */
export function FacetSearch ({ onChange, onReset, value, i18n }) {
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
        placeholder={i18n._(t('js.params.common.FacetSearch.searchFacets.placeholder')`Search facets...`)}
        autoComplete='off'
        value={value}
        onChange={onChangeCallback}
        onKeyDown={onKeyDown}
      />
      <button
        type='button'
        onClick={onReset}
        className='close'
        title={i18n._(t('js.params.common.FacetSearch.clearSearch.hoverText')`Clear Search`)}
      >
        <i className='icon-close' />
      </button>
    </fieldset>
  )
}
FacetSearch.propTypes = {
  i18n: PropTypes.shape({
    // i18n object injected by LinguiJS withI18n()
    _: PropTypes.func.isRequired
  }),
  onReset: PropTypes.func.isRequired, // func() => undefined
  onChange: PropTypes.func.isRequired, // func(value) => undefined
  value: PropTypes.string.isRequired // current input
}

export default withI18n()(FacetSearch)
