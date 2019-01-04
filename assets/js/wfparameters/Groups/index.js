import React from 'react'
import PropTypes from 'prop-types'
import ColumnSelector from '../ColumnSelector'
import DateGranularities from './DateGranularities'

export default class Groups extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input> names
    value: PropTypes.shape({
      colnames: PropTypes.string.isRequired,
      group_dates: PropTypes.bool.isRequired,
      date_granularities: PropTypes.object.isRequired
    }).isRequired,
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  onChangeColnames = (colnames) => {
    const { value, onChange } = this.props
    onChange({ ...value, colnames })
  }

  onSubmitColnames = () => {
    // Actually, we submit onChange for now
    // [2018-01-04] TODO get One Big Submit Button, and then use onSubmit.
  }

  onChangeGroupDates = (ev) => {
    const { value, onChange } = this.props
    onChange({ ...value, group_dates: ev.target.checked })
  }

  onChangeDateGranularities = (newValue) => {
    const { value, onChange } = this.props
    onChange({ ...value, date_granularities: newValue })
  }

  render () {
    const { isReadOnly, name, value, allColumns } = this.props
    const dateColnames = allColumns ? allColumns.filter(c => c.type === 'datetime').map(c => c.name) : null

    return (
      <div className='groups'>
        <ColumnSelector
          isReadOnly={isReadOnly}
          name={`${name}[colnames]`}
          initialValue={value.colnames}
          value={value.colnames}
          allColumns={allColumns}
          onChange={this.onChangeColnames}
          onSubmit={this.onSubmitColnames}
        />
        {isReadOnly ? null : (
          <div className='group-dates'>
            <label>
              <input
                type="checkbox"
                name={`${name}[group_dates]`}
                checked={value.group_dates}
                onChange={this.onChangeGroupDates}
              /> Group dates
            </label>
          </div>
        )}
        {value.group_dates ? (
          <DateGranularities
            isReadOnly={isReadOnly}
            name={name}
            value={value.date_granularities}
            colnames={value.colnames.split(',').filter(s => !!s)}
            dateColnames={dateColnames}
            onChange={this.onChangeDateGranularities}
          />
        ) : null}
      </div>
    )
  }
}
