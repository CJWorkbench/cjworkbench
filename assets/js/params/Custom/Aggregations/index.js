import React from 'react'
import PropTypes from 'prop-types'
import Aggregation from './Aggregation'

export default class Aggregations extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input> names
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
    const { value, onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = value.slice()
    newValue[index] = aggregation // may append an element
    onChange(newValue)
  }

  onDeleteAggregation = (index) => {
    const { value, onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = value.slice()
    newValue.splice(index, 1)
    onChange(newValue)
  }

  onAdd = () => {
    const { value, onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = value.slice()
    newValue.push({ operation: 'sum', colname: '', outname: '' })
    onChange(newValue)
  }

  render () {
    let { value } = this.props
    const { name, inputColumns, isReadOnly } = this.props

    if (!value || value.length === 0) {
      value = [{ operation: 'count', colname: '', outname: ''}]
    }

    const onDelete = value.length <= 1 ? null : this.onDeleteAggregation

    return (
      <div className='aggregations'>
        <h5>Operations</h5>
        <ul>
          {value.map((aggregation, index) => (
            <Aggregation
              key={index}
              isReadOnly={isReadOnly}
              name={`${name}[${index}]`}
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
            onClick={this.onAdd}
          >
            <i className='icon-add'/> Add
          </button>
        )}
      </div>
    )
  }
}
