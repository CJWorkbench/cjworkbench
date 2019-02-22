import React from 'react'
import PropTypes from 'prop-types'
import ColumnParam from '../../Column'
import RadioParam from '../../Radio.js'

export default class SortColumn extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onDelete: PropTypes.func, // func(index) => undefined, or null if delete not allowed
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    colname: PropTypes.string.isRequired, // column string
    is_ascending: PropTypes.bool.isRequired // bool indicating sort direction
  }

  onChangeDirection = (direction) => {
    const { index, colname, onChange } = this.props
    onChange(index, { colname, is_ascending: (direction === 0) })
  }

  onChangeColname = (colnameOrNull) => {
    const { index, is_ascending, onChange } = this.props
    onChange(index, { is_ascending, colname: (colnameOrNull || '') })
  }

  onClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  render () {
    const { index, name, onDelete, colname, is_ascending, isReadOnly, inputColumns } = this.props
    const sortDirection = is_ascending ? 0 : 1
    const label = index === 0 ? 'By' : 'Then by'

    return (
      <React.Fragment>
        <label>{label}</label>
        <li className='sort-column'>
          <ColumnParam
            key={index}
            name={`${name}[colname]`}
            value={colname}
            prompt='Select a column'
            isReadOnly={isReadOnly}
            inputColumns={inputColumns}
            onChange={this.onChangeColname}
          />
          )}
          <RadioParam
            name={`${name}[radio]`}
            items={'Ascending|Descending'}
            value={sortDirection}
            isReadOnly={isReadOnly}
            onChange={this.onChangeDirection}
          />
          {(onDelete && !isReadOnly) ? (
            <div className='delete'>
              <button
                className='delete'
                name={`${name}[delete]`}
                onClick={this.onClickDelete}
              >
                <i className='icon-close' />
              </button>
            </div>
          ) : null}
        </li>
      </React.Fragment>
    )
  }
}
