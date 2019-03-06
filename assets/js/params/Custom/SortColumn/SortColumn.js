import React from 'react'
import PropTypes from 'prop-types'
import ColumnParam from '../../Column'
import RadioParam from '../../Radio.js'


const AscendingParamOptions = [
  { value: true, label: 'Ascending' },
  { value: false, label: 'Descending' }
]
function AscendingParam (props) {
  return (
    <RadioParam
      enumOptions={AscendingParamOptions}
      {...props}
    />
  )
}
AscendingParam.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // for <input name=...>
  fieldId: PropTypes.string.isRequired, // <input id=...>
  onChange: PropTypes.func.isRequired, // func(index, value) => undefined
  value: PropTypes.bool.isRequired
}



export default class SortColumn extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onDelete: PropTypes.func, // func(index) => undefined, or null if delete not allowed
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    value: PropTypes.shape({
      colname: PropTypes.string.isRequired, // column string
      is_ascending: PropTypes.bool.isRequired // sort direction
    }).isRequired
  }

  onChangeIsAscending = (isAscending) => {
    const { index, value: { colname }, onChange } = this.props
    onChange(index, { colname, is_ascending: isAscending })
  }

  onChangeColname = (colnameOrNull) => {
    const { index, value: { is_ascending }, onChange } = this.props
    onChange(index, { is_ascending, colname: (colnameOrNull || '') })
  }

  onClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  render () {
    const { index, value, name, fieldId, onDelete, isReadOnly, inputColumns } = this.props
    const label = index === 0 ? 'By' : 'Then by'

    return (
      <React.Fragment>
        <label>{label}</label>
        <li className='sort-column'>
          <ColumnParam
            key={index}
            name={`${name}[colname]`}
            fieldId={`${name}_colname`}
            value={value.colname}
            prompt='Select a column'
            isReadOnly={isReadOnly}
            inputColumns={inputColumns}
            onChange={this.onChangeColname}
          />
          <AscendingParam
            name={`${name}[is_ascending]`}
            fieldId={`${name}_is_ascending`}
            value={value.is_ascending}
            isReadOnly={isReadOnly}
            onChange={this.onChangeIsAscending}
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
