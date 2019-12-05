import React from 'react'
import PropTypes from 'prop-types'
import DateGranularity from './DateGranularity'
import { Trans } from '@lingui/macro'

function DateGranularityList ({ isReadOnly, name, colnames, value, onChange }) {
  return (
    <ul>
      {colnames.map(colname => (
        <li key={colname}>
          <DateGranularity
            isReadOnly={isReadOnly}
            name={`${name}[${colname}]`}
            colname={colname}
            value={value[colname] || null}
            onChange={onChange}
          />
        </li>
      ))}
    </ul>
  )
}

export default class DateGranularities extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <select> names
    value: PropTypes.objectOf(PropTypes.oneOf('STHDMQY'.split('')).isRequired).isRequired,
    colnames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    dateColnames: PropTypes.arrayOf(PropTypes.string.isRequired), // null if unknown
    onChange: PropTypes.func.isRequired, // func(newObject) => undefined
    addConvertToDateModule: PropTypes.func.isRequired // func() => undefined
  }

  handleChangeDateGranularity = (colname, granularity) => {
    const { value, onChange } = this.props
    const newValue = { ...value }
    if (granularity) {
      newValue[colname] = granularity
    } else {
      delete newValue[colname]
    }
    onChange(newValue)
  }

  render () {
    const { isReadOnly, name, value, colnames, dateColnames, addConvertToDateModule } = this.props

    const focusColnames = colnames.filter(c => dateColnames !== null && dateColnames.includes(c))

    return (
      <div className='date-granularities'>
        {focusColnames.length > 0 ? (
          <DateGranularityList
            isReadOnly={isReadOnly}
            name={name}
            colnames={focusColnames}
            value={value}
            onChange={this.handleChangeDateGranularity}
          />
        ) : (
          <div className='no-date-selected'>
            {(dateColnames !== null && dateColnames.length === 0) ? (
              <>
                <p><Trans id='js.params.Custom.Groups.DateGranularities.noDateAndTimeToGroup'>There are no Date and Time columns to group by date </Trans></p>
                <button
                  type='button'
                  name={`${name}[add-module]`}
                  className='quick-fix action-button button-blue'
                  onClick={addConvertToDateModule}
                >
                  <Trans id='js.params.Custom.Groups.DateGranularities.convertColumns'>Convert columns</Trans>
                </button>
              </>
            ) : (
              <p><Trans id='js.params.Custom.Groups.DateGranularities.selectDateAndTimeToGroup'>Select a Date and Time column to group it by date</Trans></p>
            )}
          </div>
        )}
      </div>
    )
  }
}
