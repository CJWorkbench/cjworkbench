// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'
import Select from 'react-select'

export default class ColumnSelector extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    value: PropTypes.string.isRequired, // e.g., 'A,B'; may be '' but not null
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })),
    onChange: PropTypes.func.isRequired // onChange('A,B') => undefined
  }

  get selectedColumns() {
    const { value } = this.props
    return value ? value.split(',') : []
  }

  onClickSelectAll = () => {
    const { allColumns } = this.props
    const names = (allColumns || []).map(x => x.name)
    this.props.onChange(names.join(','))
  }

  onClickSelectNone = () => {
    this.props.onChange('')
  }

  onSelectColumn = (ev) => {
    const columns = ev.map(column => column.value)
    this.props.onChange(columns.join(','))
  }

  compareSelected = (a, b) => {
    const indexA = this.props.allColumns.findIndex(p => p.name === a)
    const indexB = this.props.allColumns.findIndex(p => p.name === b)
    return indexA - indexB
  }

  render() {
    const { allColumns, isReadOnly, name } = this.props

    if (allColumns === null) {
      return (
        <div className='loading'></div>
      )
    }

    const columnOptions = allColumns.map(column => (
      {
        label: column.name,
        value: column.name
      }
    ))

    const selectedColumns = this.selectedColumns.sort(this.compareSelected).map(column => (
      {
        label: column,
        value: column
      }
    ))

    return (
      // The name attributes in the buttons are used for selection in tests. Do not change them.
      <div>
        <div className="d-flex mb-2 mt-2 ">
          <button
            disabled={isReadOnly}
            name={`${name}-select-all`}
            title='Select All'
            onClick={this.onClickSelectAll}
            className='mc-select-all content-4 t-d-gray'
            >
            All
          </button>
          <button
            disabled={isReadOnly}
            name={`${name}-select-none`}
            title='Select None'
            onClick={this.onClickSelectNone}
            className='mc-select-none content-4 t-d-gray'
            >
            None
          </button>
        </div>
        <Select
          isMulti
          name='columns'
          options={columnOptions}
          menuPortalTarget={document.body}
          className='react-select'
          classNamePrefix='react-select'
          onChange={this.onSelectColumn}
          value={selectedColumns}
          isClearable={false}
          placeholder='Select columns'
        />
      </div>
    )
  }
}
