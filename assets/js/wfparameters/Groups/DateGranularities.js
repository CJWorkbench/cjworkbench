import React from 'react'
import PropTypes from 'prop-types'
import DateGranularity from './DateGranularity'

export default class DateGranularities extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <select> names
    value: PropTypes.objectOf(PropTypes.oneOf('STHDMQY').isRequired).isRequired,
    colnames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    dateColnames: PropTypes.arrayOf(PropTypes.string.isRequired), // null if unknown
    onChange: PropTypes.func.isRequired // func(newObject) => undefined
  }

  onChangeDateGranularity = (colname, granularity) => {
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
    const { isReadOnly, value, colnames, dateColnames } = this.props

    const focusColnames = colnames.filter(c => dateColnames !== null && dateColnames.includes(c))

    return (
      <div className='date-granularities'>
        <ul>
          {focusColnames.map(colname => (
            <li>
              <DateGranularity
                isReadOnly={isReadOnly}
                name={`${name}[date_granularities][${colname}]`}
                colname={colname}
                value={value[colname] || null}
                onChange={this.onChangeDateGranularity}
              />
            </li>
          ))}
        </ul>
      </div>
    )
  }
}
