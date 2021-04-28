import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import Multicolumn from '../../Multicolumn'
import DateGranularities from './DateGranularities'
import SelectedTemporalColumn from './SelectedTemporalColumn'

export default function Groups (props) {
  const {
    isReadOnly,
    name,
    fieldId,
    value,
    upstreamValue,
    inputColumns,
    onChange,
    applyQuickFix
  } = props

  const handleChangeColnames = React.useCallback(
    colnames => { onChange({ ...value, colnames }) },
    [onChange, value]
  )

  const handleChangeGroupDates = React.useCallback(
    ev => { onChange({ ...value, group_dates: ev.target.checked }) },
    [onChange, value]
  )

  const selectedTimestampColnames = (inputColumns || [])
    .filter(c => value.colnames.includes(c.name) && c.type === 'timestamp')
    .map(c => c.name)
  const selectedTemporalColumns = (inputColumns || [])
    .filter(c => value.colnames.includes(c.name) && (c.type === 'timestamp' || c.type === 'date'))

  return (
    <div className='groups'>
      <Multicolumn
        isReadOnly={isReadOnly}
        name={`${name}[colnames]`}
        fieldId={`${fieldId}_colnames`}
        upstreamValue={value.colnames}
        value={value.colnames}
        inputColumns={inputColumns}
        onChange={handleChangeColnames}
      />
      {selectedTemporalColumns.map(column => (
        <SelectedTemporalColumn
          isReadOnly={isReadOnly}
          key={column.name}
          column={column}
          applyQuickFix={applyQuickFix}
        />
      ))}
      {(value.group_dates || upstreamValue.group_dates) && selectedTimestampColnames.length
        ? (
          <>
            <div className='group-dates'>
              <label>
                <input
                  type='checkbox'
                  name={`${name}[group_dates]`}
                  disabled={isReadOnly}
                  checked={value.group_dates}
                  onChange={handleChangeGroupDates}
                />{' '}
                <Trans id='js.params.Custom.Groups.groupDates'>Group dates [deprecated]</Trans>
              </label>
            </div>
            {value.group_dates
              ? (
                <DateGranularities
                  isReadOnly={isReadOnly}
                  name={`${name}[date_granularities]`}
                  fieldId={`${fieldId}_date_granularities`}
                  value={value.date_granularities}
                  colnames={selectedTimestampColnames}
                  applyQuickFix={applyQuickFix}
                />
              )
              : null}
          </>
          )
        : null}
    </div>
  )
}
Groups.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // for <input> names
  fieldId: PropTypes.string.isRequired, // <input id="...">
  value: PropTypes.shape({
    colnames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    group_dates: PropTypes.bool.isRequired,
    date_granularities: PropTypes.object.isRequired
  }).isRequired,
  inputColumns: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'date', 'timestamp']).isRequired,
      unit: PropTypes.oneOf(['day', 'week', 'month', 'quarter', 'year']) // if type === 'date'
    })
  ), // or null if unknown
  onChange: PropTypes.func.isRequired, // func(value) => undefined
  applyQuickFix: PropTypes.func.isRequired // func(action) => undefined
}
