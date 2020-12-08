import React from 'react'
import PropTypes from 'prop-types'
import { AndOrPropType } from './PropTypes'
import { Trans } from '@lingui/macro'

export default function AddButton ({ isReadOnly, className, name, operation, isFirst, onClickAddAnd, onClickAddOr }) {
  if (isReadOnly) return null

  return (
    <div className={className}>
      {(isFirst || operation === 'and') ? (
        <button
          type='button'
          name={`${name}[and]`}
          className='and'
          onClick={onClickAddAnd}
        >
          <Trans id='js.params.Condition.AddButton.and' comment='The logical AND operator'>AND</Trans>
        </button>
      ) : null}
      {(isFirst || operation === 'or') ? (
        <button
          type='button'
          name={`${name}[or]`}
          className='or'
          onClick={onClickAddOr}
        >
          <Trans id='js.params.Condition.AddButton.or' comment='The logical OR operator'>OR</Trans>
        </button>
      ) : null}
    </div>
  )
}
AddButton.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  operation: AndOrPropType.isRequired,
  isFirst: PropTypes.bool.isRequired,
  onClickAddAnd: PropTypes.func.isRequired, // func() => undefined
  onClickAddOr: PropTypes.func.isRequired // func() => undefined
}
