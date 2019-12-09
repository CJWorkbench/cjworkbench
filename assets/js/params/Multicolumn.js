// Choose some columns
import React from 'react'
import PropTypes from 'prop-types'
import ReactSelect from './common/react-select'
import { components } from 'react-select'
import { MaybeLabel } from './util'
import { t, Trans } from '@lingui/macro'
import { withI18n } from '@lingui/react'

class MenuList extends React.PureComponent {
  handleClickSelectAll = () => {
    const { setValue, selectProps } = this.props
    const { options } = selectProps
    setValue(options)
  }

  handleClickSelectNone = () => {
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
            onClick={this.handleClickSelectAll}
            className='multicolumn-select-all'
          >
            <Trans id='js.params.Multicolumn.MenuList.selectAllButton'>Select all</Trans>
          </button>
          <button
            name={`${name}-select-none`}
            type='button'
            onClick={this.handleClickSelectNone}
            className='multicolumn-select-none'
          >
            <Trans id='js.params.Multicolumn.MenuList.clearButton'>clear</Trans>
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

export class Multicolumn extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange('A,B') => undefined
    addMenuListClassName: PropTypes.string, // default undefined
    noOptionsMessage: PropTypes.string, // default 'No options'
    value: PropTypes.oneOfType([
      PropTypes.string.isRequired, // e.g., 'A,B'; may be '' but not null
      PropTypes.arrayOf(PropTypes.string.isRequired).isRequired // may be [] but not null
    ]).isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    }))
  }

  // For a transition period, we support "multicolumn" values being String.
  // That changes a bit of logic.
  get isDeprecatedMulticolumnParam () {
    return !Array.isArray(this.props.value)
  }

  // Compatibility layer: return this.props.value as an Array even if the value
  // is [DEPRECATED} String.
  get value () {
    const { value } = this.props
    if (this.isDeprecatedMulticolumnParam) {
      return value.split(',').filter(s => s !== '')
    } else {
      return value
    }
  }

  handleChangeColumns = (columns) => {
    const value = this.isDeprecatedMulticolumnParam ? columns.join(',') : columns
    this.props.onChange(value)
  }

  render () {
    const { inputColumns, isReadOnly, fieldId, name, placeholder, label, addMenuListClassName, noOptionsMessage, i18n } = this.props

    const columnOptions = (inputColumns || []).map(column => (
      {
        label: column.name,
        value: column.name
      }
    ))

    return (
      // The name attributes in the buttons are used for selection in tests. Do not change them.
      <>
        <MaybeLabel fieldId={fieldId} label={label} />
        <ReactSelect
          isMulti
          isReadOnly={isReadOnly}
          name={name}
          inputId={fieldId}
          options={columnOptions}
          isLoading={inputColumns === null}
          onChange={this.handleChangeColumns}
          addMenuListClassName={addMenuListClassName}
          noOptionsMessage={noOptionsMessage}
          components={Components}
          value={this.value}
          placeholder={placeholder || i18n._(t('js.params.Multicolumn.selectColumn.placeholder')`Select columns`)}
        />
      </>
    )
  }
}
export default withI18n()(Multicolumn)
