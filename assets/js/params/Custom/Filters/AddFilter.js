import React from 'react'
import PropTypes from 'prop-types'
import { OperatorPropType } from './PropTypes'
import { Trans } from '@lingui/macro'

export default function AddFilter ({ isReadOnly, name, operator, nFilters, onClickAddAnd, onClickAddOr }) {
  if (isReadOnly) return null

  return (
    <div className='add-filter'>
      {(nFilters <= 1 || operator === 'and') ? (
        <button
          type='button'
          name={`${name}[and]`}
          className='and'
          onClick={onClickAddAnd}
        >
          <Trans id='js.params.Custom.Filters.AddFilter.and' description='This is the logical AND function.'>AND</Trans>
        </button>
      ) : null}
      {(nFilters <= 1 || operator === 'or') ? (
        <button
          type='button'
          name={`${name}[or]`}
          className='or'
          onClick={onClickAddOr}
        >
          <Trans id='js.params.Custom.Filters.AddFilter.or' description='This is the logical OR function.'>OR</Trans>
        </button>
      ) : null}
    </div>
  )
}
AddFilter.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  operator: OperatorPropType.isRequired,
  nFilters: PropTypes.number.isRequired,
  onClickAddAnd: PropTypes.func.isRequired, // func() => undefined
  onClickAddOr: PropTypes.func.isRequired // func() => undefined
}
