import React from 'react'
import PropTypes from 'prop-types'
import Multicolumn from '../../Multicolumn'
import DateGranularities from './DateGranularities'

export default class Groups extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input> names
    fieldId: PropTypes.string.isRequired, // <input id="...">
    value: PropTypes.shape({
      colnames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
      group_dates: PropTypes.bool.isRequired,
      date_granularities: PropTypes.object.isRequired
    }).isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(value) => undefined
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
  }

  onChangeColnames = (colnames) => {
    const { value, onChange } = this.props
    onChange({ ...value, colnames })
  }

  onChangeGroupDates = (ev) => {
    const { value, onChange } = this.props
    onChange({ ...value, group_dates: ev.target.checked })
  }

  onChangeDateGranularities = (newValue) => {
    const { value, onChange } = this.props
    onChange({ ...value, date_granularities: newValue })
  }

  addConvertToDateModule = () => {
    this.props.applyQuickFix('prependModule', [ 'convert-date', {} ])
  }

  render () {
    const { isReadOnly, name, fieldId, value, inputColumns } = this.props
    const dateColnames = inputColumns ? inputColumns.filter(c => c.type === 'datetime').map(c => c.name) : null

    return (
      <div className='groups'>
        <Multicolumn
          isReadOnly={isReadOnly}
          name={`${name}[colnames]`}
          fieldId={`${fieldId}_colnames`}
          upstreamValue={value.colnames}
          value={value.colnames}
          inputColumns={inputColumns}
          onChange={this.onChangeColnames}
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
            name={`${name}[date_granularities]`}
            fieldId={`${fieldId}_date_granularities`}
            value={value.date_granularities}
            colnames={value.colnames}
            dateColnames={dateColnames}
            onChange={this.onChangeDateGranularities}
            addConvertToDateModule={this.addConvertToDateModule}
          />
        ) : null}
      </div>
    )
  }
}
