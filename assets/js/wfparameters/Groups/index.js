import React from 'react'
import PropTypes from 'prop-types'
import ColumnSelector from '../ColumnSelector'

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
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  onChangeColnames = (colnames) => {
    const { value, onChange } = this.props
    onChange({ ...value, colnames })
  }

  onSubmitColnames = () => {
    // Actually, we submit onChange for now [2018-01-04] TODO fix this
  }

  render () {
    const { isReadOnly, name, value, allColumns } = this.props

    return (
      <div className='groups'>
        <ColumnSelector
          name={`${name}[colnames]`}
          isReadOnly={isReadOnly}
          initialValue={value.colnames}
          value={value.colnames}
          allColumns={allColumns}
          onChange={this.onChangeColnames}
          onSubmit={this.onSubmitColnames}
        />
      </div>
    )
  }
}
