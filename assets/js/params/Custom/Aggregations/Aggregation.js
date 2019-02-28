import React from 'react'
import PropTypes from 'prop-types'
import Operation from './Operation'
import ColumnParam from '../../Column'

export default class Aggregation extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    fieldId: PropTypes.string.isRequired, // for <input id=...>
    index: PropTypes.number.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onDelete: PropTypes.func, // func(index) => undefined, or null if delete not allowed
    operation: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'min', 'max', 'first']).isRequired,
    colname: PropTypes.string.isRequired,
    outname: PropTypes.string.isRequired // may be empty
  }

  onChangeOperation = (ev) => {
    const { colname, index, outname, onChange } = this.props
    onChange(index, { colname, outname, operation: ev.target.value })
  }

  onChangeColname = (colnameOrNull) => {
    const { outname, operation, index, onChange } = this.props
    onChange(index, { outname, operation, colname: (colnameOrNull || '') })
  }

  onChangeOutname = (ev) => {
    const { colname, operation, index, onChange } = this.props
    onChange(index, { colname, operation, outname: ev.target.value })
  }

  onClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  get placeholder () {
    // Duplicated from grroupby/groupby.py
    const { operation, colname } = this.props

    if (operation === 'size') return 'Group Size'

    if (colname === '') {
      // reduce clutter -- groupby.py won't add this operation anyway
      return ''
    }

    switch (operation) {
      case 'nunique': return `Unique count of ${colname}`
      case 'sum': return `Sum of ${colname}`
      case 'mean': return `Average of ${colname}`
      case 'min': return `Minimum of ${colname}`
      case 'max': return `Maximum of ${colname}`
      case 'first': return `First of ${colname}`
      default: return '(default)'
    }
  }

  render () {
    const { name, fieldId, index, onDelete, operation, colname, outname, inputColumns, isReadOnly } = this.props

    return (
      <li className='aggregation'>
        <Operation
          isReadOnly={isReadOnly}
          name={`${name}[operation]`}
          fieldId={`${fieldId}_operation`}
          value={operation}
          onChange={this.onChangeOperation}
        />
        {operation === 'size' ? null : (
          <ColumnParam
            name={`${name}[colname]`}
            fieldId={`${fieldId}_colname`}
            value={colname}
            prompt='Select a column'
            isReadOnly={isReadOnly}
            inputColumns={inputColumns}
            onChange={this.onChangeColname}
          />
        )}
        <label className='outname'>
          <span className='name'>Name</span>
          <input
            className='outname' 
            name={`${name}[outname]`}
            id={`${fieldId}_outname`}
            value={outname}
            onChange={this.onChangeOutname}
            placeholder={this.placeholder}
          />
        </label>
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
    )
  }
}
