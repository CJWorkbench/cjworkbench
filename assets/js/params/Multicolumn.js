// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'
import ReactSelect from './common/react-select'
import { components } from 'react-select'
import { MaybeLabel } from './util'

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
    const { name, addMenuListClassName } = this.props.selectProps

    const className = ['react-select__menu-list', 'react-select__menu-list--is-multi']
    if (addMenuListClassName) className.push(addMenuListClassName)

    return (
      <components.MenuList {...this.props} className={className.join(' ')}>
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
    addMenuListClassName: PropTypes.string, // default undefined
    noOptionsMessage: PropTypes.string, // default 'No options'
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

  onChangeColumns = (columns) => {
    this.props.onChange(columns.join(','))
  }

  compareSelected = (a, b) => {
    const indexA = this.props.inputColumns.findIndex(p => p.name === a)
    const indexB = this.props.inputColumns.findIndex(p => p.name === b)
    return indexA - indexB
  }

  render() {
    const { inputColumns, isReadOnly, fieldId, name, placeholder, label, addMenuListClassName, noOptionsMessage } = this.props

    const columnOptions = (inputColumns || []).map(column => (
      {
        label: column.name,
        value: column.name
      }
    ))

    return (
      // The name attributes in the buttons are used for selection in tests. Do not change them.
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <ReactSelect
          isMulti
          isReadOnly={isReadOnly}
          name={name}
          inputId={fieldId}
          options={columnOptions}
          isLoading={inputColumns === null}
          onChange={this.onChangeColumns}
          addMenuListClassName={addMenuListClassName}
          noOptionsMessage={noOptionsMessage}
          components={Components}
          value={this.selectedColumns}
          placeholder={placeholder || 'Select columns'}
        />
      </React.Fragment>
    )
  }
}
