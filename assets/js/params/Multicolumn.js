// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'
import Select, { components } from 'react-select'
import { ReactSelectStyles } from './Column'


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
            type='button'
            onClick={this.onClickSelectAll}
            className='multicolumn-select-all'
          >
            Select all
          </button>
          <button
            name={`${name}-select-none`}
            type='button'
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
    onChange: PropTypes.func.isRequired, // onChange('A,B') => undefined
    value: PropTypes.string.isRequired, // e.g., 'A,B'; may be '' but not null
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    }))
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

  onSelectColumn = (ev) => {
    const columns = ev.map(column => column.value)
    this.props.onChange(columns.join(','))
  }

  compareSelected = (a, b) => {
    const indexA = this.props.inputColumns.findIndex(p => p.name === a)
    const indexB = this.props.inputColumns.findIndex(p => p.name === b)
    return indexA - indexB
  }

  render() {
    const { inputColumns, isReadOnly, name, value, label } = this.props

    if (inputColumns === null) {
      return (
        <div className='column-selector loading'></div>
      )
    }

    const columnOptions = inputColumns.map(column => (
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
      <React.Fragment>
        {label ? (
          <label>{label}</label>
        ) : null}
        <Select
          isMulti
          isDisabled={isReadOnly}
          name={name}
          options={columnOptions}
          menuPortalTarget={document.body}
          className='react-select multicolumn'
          classNamePrefix='react-select'
          styles={ReactSelectStyles}
          onChange={this.onSelectColumn}
          components={Components}
          value={selectedColumns}
          isClearable={false}
          placeholder='Select columns'
        />
      </React.Fragment>
    )
  }
}
