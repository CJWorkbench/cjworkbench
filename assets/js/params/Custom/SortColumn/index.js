import React from 'react'
import PropTypes from 'prop-types'
import ColumnParam from '../../Column'
import RadioParam from '../../Radio.js'
import SortColumn from './SortColumn.js'

const DefaultValue = [{ colname: '', is_ascending: true }]

export default class SortColumns extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    value: PropTypes.arrayOf(PropTypes.shape({
      column: PropTypes.string.isRequired, // column string
      is_ascending: PropTypes.bool.isRequired // bool indicating sort direction
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
 * Migrate v0 params, given value, or default of {operation:size} if empty.
 *
 * groupby.py uses this default. Read comments there to see why.
 */
  get value () {
    const actual = this.props.value
    if ('column' in actual) {


      return
    } else if (actual.length === 0) {
      return DefaultValue
    } else {
      return actual
    }
  }

  render () {
    const { name, isReadOnly, inputColumns } = this.props
    const value = this.value
    const onDelete = value.length <= 1 ? null : this.onDeleteSortColumn

    return (
      <React.Fragment>
        <ul>
          {value.map((sortColumn, index) => (
            <SortColumn
              isReadOnly={isReadOnly}
              index={index}
              inputColumns={inputColumns}
              name={`${name}[${index}]`}
              onChange={this.onChangeSortColumn}
              {...sortColumn}
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
            <i className='icon-add'/> Add
          </button>
        )}
      </React.Fragment>
    )
  }
}
