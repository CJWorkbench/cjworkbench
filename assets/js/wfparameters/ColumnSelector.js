// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'

export default class ColumnSelector extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    value: PropTypes.string.isRequired, // e.g., 'A,B'; may be '' but not null
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })),
    onChange: PropTypes.func.isRequired // onChange('A,B') => undefined
  }

  get selectedColumns() {
    const { value } = this.props
    return value ? value.split(',') : []
  }

  onClickSelectAll = () => {
    const { inputColumns } = this.props
    const names = (inputColumns || []).map(x => x.name)
    this.props.onChange(names.join(','))
  }

  onClickSelectNone = () => {
    this.props.onChange('')
  }

  onChangeColumn = (ev) => {
    const column = ev.target.value
    const checked = ev.target.checked

    const columns = this.selectedColumns
    let changed = false
    if (checked && columns.indexOf(column) === -1) {
      columns.push(column)
      changed = true
    } else if (!checked && columns.indexOf(column) !== -1) {
      columns.splice(columns.indexOf(column), 1)
      changed = true
    }

    if (changed) {
      this.props.onChange(columns.join(','))
    }
  }

  render() {
    const { inputColumns, isReadOnly, name } = this.props
    const selected = this.selectedColumns

    if (inputColumns === null) {
      return (
        <div className='loading'>
        </div>
      )
    }

    // use nowrap style to ensure checkbox label is always on same line as checkbox
    const checkboxes = inputColumns.map(column => (
      <label className='checkbox-container' style={{'whiteSpace': 'nowrap'}} key={column.name}>
        <input
          type='checkbox'
          readOnly={isReadOnly}
          name={`${name}[${column.name}]`}
          checked={selected.indexOf(column.name) !== -1}
          onChange={this.onChangeColumn}
        />
        <span className='t-d-gray checkbox-content content-3'>{column.name}</span>
      </label>
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
        <div className='container list-wrapper'>
          <div className='row list-scroll'>
            {checkboxes}
          </div>
        </div>
      </div>
    )
  }
}
