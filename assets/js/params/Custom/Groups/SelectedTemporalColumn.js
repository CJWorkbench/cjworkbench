import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'

export default function SelectedTemporalColumn (props) {
  const { isReadOnly, column, applyQuickFix } = props
  const { name, type, unit = null } = column

  const valueTypes = type === 'timestamp'
    ? t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.timestamps', message: 'timestamps' })
    : {
        day: t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.days', message: 'days' }),
        week: t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.weeks', message: 'weeks' }),
        month: t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.months', message: 'months' }),
        quarter: t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.quarters', message: 'quarters' }),
        year: t({ id: 'js.params.Custom.Groups.SelectedTemporalColumn.type.years', message: 'years' })
      }[unit]

  const handleClickConvertTimestampToDate = React.useCallback(
    ev => {
      applyQuickFix({
        type: 'prependStep',
        moduleSlug: 'converttimestamptodate',
        partialParams: { colnames: [name], unit: 'day' }
      })
    },
    [applyQuickFix, name, unit, type]
  )

  return (
    <div className='selected-temporal-column'>
      <p>
        <Trans id='js.params.Custom.Groups.SelectedTemporalColumn' values={{ name, valueTypes }}>
          “{name}” holds <strong>{valueTypes}.</strong>
        </Trans>
      </p>
      {isReadOnly
        ? null
        : (type === 'timestamp'
            ? (
              <button type='button' onClick={handleClickConvertTimestampToDate}>
                <Trans id='js.params.Custom.Groups.SelectedTemporalColumn.convertToDate'>Convert to Date</Trans>
              </button>
              )
            : null)}
    </div>
  )
}
SelectedTemporalColumn.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  applyQuickFix: PropTypes.func.isRequired, // func(action) => undefined
  column: PropTypes.oneOfType([
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['timestamp']).isRequired
    }).isRequired,
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['date']).isRequired,
      unit: PropTypes.oneOf(['day', 'week', 'month', 'quarter', 'year']).isRequired
    }).isRequired
  ]).isRequired
}
