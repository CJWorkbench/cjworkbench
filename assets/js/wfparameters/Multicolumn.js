// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'
import Select, { components } from 'react-select'


class MenuList extends React.PureComponent {
  onClickSelectAll = () => {
    const { setValue, selectProps } = this.props
    const { options } = selectProps
    setValue(options)
  }

  onClickSelectNone = () => {
    const { clearValue } = this.props
    clearValue()
  }

  render () {
    const { name } = this.props.selectProps

    return (
      <components.MenuList {...this.props}>
        <div className='multicolumn-select-all-none'>
          <button
            name={`${name}-select-all`}
            onClick={this.onClickSelectAll}
            className='multicolumn-select-all'
          >
            Select all
          </button>
          <button
            name={`${name}-select-none`}
            onClick={this.onClickSelectNone}
            className='multicolumn-select-none'
          >
            clear
          </button>
        </div>
        {this.props.children}
      </components.MenuList>
    )
  }
}

const Components = {
  MenuList
}

export default class Multicolumn extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    initialValue: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // onChange('A,B') => undefined
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    value: PropTypes.string.isRequired, // e.g., 'A,B'; may be '' but not null
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    }))
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
    const { allColumns, isReadOnly, name, initialValue, value } = this.props

    if (allColumns === null) {
      return (
        <div className='column-selector loading'></div>
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
    const maybeButton = initialValue === value ? null : (
      <button title="submit" onClick={this.props.onSubmit}>
        <i className="icon-play" />
      </button>
    )
    return (
      // The name attributes in the buttons are used for selection in tests. Do not change them.
      <div className='column-selector'>
        <div className="multi-select-input-group">
          <Select
            isMulti
            isDisabled={isReadOnly}
            name={name}
            options={columnOptions}
            menuPortalTarget={document.body}
            className='react-select'
            classNamePrefix='react-select'
            onChange={this.onSelectColumn}
            components={Components}
            value={selectedColumns}
            isClearable={false}
            placeholder='Select columns'
          />
          {maybeButton}
        </div>
      </div>
    )
  }
}
