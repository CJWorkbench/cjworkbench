import React from 'react'
import PropTypes from 'prop-types'
import Aggregation from './Aggregation'

const DefaultValue = [{ operation: 'size', colname: '', outname: '' }]
const DefaultAddValue = { operation: 'sum', colname: '', outname: '' }

export default class Aggregations extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    value: PropTypes.arrayOf(PropTypes.shape({
      operation: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'min', 'max', 'first']).isRequired,
      colname: PropTypes.string.isRequired,
      outname: PropTypes.string.isRequired
    }).isRequired).isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func([aggregations]) => undefined
  }

  onChangeAggregation = (index, aggregation) => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue[index] = aggregation // may append an element
    onChange(newValue)
  }

  onDeleteAggregation = (index) => {
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
    newValue.push(DefaultAddValue)
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
    const { name, fieldId, inputColumns, isReadOnly } = this.props
    const value = this.value
    const onDelete = value.length <= 1 ? null : this.onDeleteAggregation

    return (
      <>
        <label>Operations</label>
        <ul>
          {value.map((aggregation, index) => (
            <Aggregation
              key={index}
              isReadOnly={isReadOnly}
              name={`${name}[${index}]`}
              fieldId={`${fieldId}_${index}`}
              index={index}
              inputColumns={inputColumns}
              {...aggregation}
              onChange={this.onChangeAggregation}
              onDelete={onDelete}
            />
          ))}
        </ul>
        {isReadOnly ? null : (
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
