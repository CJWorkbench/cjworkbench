import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

function SortIndicator ({ isActive, isAscending }) {
  if (!isActive) return null

  const icon = isAscending ? 'icon-sort-up' : 'icon-sort-down'

  return (
    <i className={`icon ${icon}`} />
  )
}

export default function ValueSortSelect ({ value, onChange }) {
  const { by, isAscending } = value
  const onClickValue = React.useCallback(() => {
    onChange({
      by: 'value',
      isAscending: by === 'value' ? !isAscending : true
    })
  })
  const onClickCount = React.useCallback(() => {
    onChange({
      by: 'count',
      isAscending: by === 'count' ? !isAscending : false
    })
  })

  return (
    <div className='value-sort-select'>
      <button className={by === 'value' ? 'active' : ''} name='by-value' type='button' onClick={onClickValue}>
        <Trans id='js.params.common.ValueSortSelect.value'>Value</Trans>
        <SortIndicator
          isActive={by === 'value'}
          isAscending={isAscending}
        />
      </button>
      <button className={by === 'count' ? 'active' : ''} name='by-count' type='button' onClick={onClickCount}>
        <SortIndicator
          isActive={by === 'count'}
          isAscending={isAscending}
        />
        <Trans id='js.params.common.ValueSortSelect.rows'>Rows</Trans>
      </button>
    </div>
  )
}
ValueSortSelect.propTypes = {
  value: PropTypes.shape({
    by: PropTypes.oneOf(['value', 'count']).isRequired,
    isAscending: PropTypes.bool.isRequired
  }).isRequired,
  onChange: PropTypes.func.isRequired // func({ by, isAscending }) => undefined
}
