import React from 'react'
import PropTypes from 'prop-types'
import SortColumn from './SortColumn.js'

const DefaultValue = [{ colname: '', is_ascending: true }]

export default class SortColumns extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    fieldId: PropTypes.string.isRequired, // for <input id=...>
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    value: PropTypes.arrayOf(PropTypes.shape({
      colname: PropTypes.string.isRequired, // column string
      is_ascending: PropTypes.bool.isRequired // sort direction
    }).isRequired).isRequired
  }

  onChangeSortColumn = (index, sortColumn) => {
    const { value, onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = value.slice()
    newValue[index] = sortColumn // may append an element
    onChange(newValue)
  }

  onDeleteSortColumn = (index) => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue.splice(index, 1)
    onChange(newValue)
  }

  onAdd = () => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue.push(DefaultValue[0])
    onChange(newValue)
  }

  /**
   * Given value, or default of {operation:size} if empty.
   *
   * groupby.py uses this default. Read comments there to see why.
   */
  get value () {
    const actual = this.props.value
    if (actual.length === 0) {
      return DefaultValue
    } else {
      return actual
    }
  }

  render () {
    const { name, fieldId, isReadOnly, inputColumns } = this.props
    const value = this.value
    const onDelete = value.length <= 1 ? null : this.onDeleteSortColumn

    return (
      <>
        <ul>
          {value.map((itemValue, index) => (
            <SortColumn
              key={index}
              isReadOnly={isReadOnly}
              index={index}
              inputColumns={inputColumns}
              value={itemValue}
              name={`${name}[${index}]`}
              fieldId={`${fieldId}_${index}`}
              onChange={this.onChangeSortColumn}
              onDelete={onDelete}
            />
          ))}
        </ul>
        {(isReadOnly || !inputColumns || value.length >= inputColumns.length) ? null : (
          <button
            type='button'
            className='add'
            name={`${name}[add]`}
            onClick={this.onAdd}
          >
            <i className='icon-add' /> Add
          </button>
        )}
      </>
    )
  }
}
