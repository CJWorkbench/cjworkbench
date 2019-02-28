import React from 'react'
import PropTypes from 'prop-types'
import { FiltersPropType } from './PropTypes'
import Filter from './Filter'
import FilterOperator from './FilterOperator'
import AddFilter from './AddFilter'

const DefaultFilter = {
  operator: 'and',
  subfilters: [
    { colname: '', condition: '', value: '', case_sensitive: false }
  ]
}

const DefaultFilters = {
  operator: 'and',
  filters: [ DefaultFilter ],
}

export default class Filters extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    value: FiltersPropType.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired
  }

  get value () {
    const { value } = this.props

    if (!value || !value.filters || !value.filters.length || !value.operator) {
      return DefaultFilters
    } else {
      return value
    }
  }

  addOperator (operator) {
    const value = this.value
    const newValue = {
      ...value,
      operator,
      filters: [ ...value.filters, DefaultFilter ]
    }
    this.props.onChange(newValue)
  }
  onClickAddAnd = () => this.addOperator('and')
  onClickAddOr = () => this.addOperator('or')

  onDeleteFilter = (index) => {
    const value = this.value
    const newFilters = value.filters.slice()
    newFilters.splice(index, 1)
    const newValue = {
      ...value,
      filters: newFilters
    }
    this.props.onChange(newValue)
  }

  onChangeFilter = (index, filter) => {
    const value = this.value
    const newFilters = value.filters.slice()
    newFilters[index] = filter
    const newValue = {
      ...value,
      filters: newFilters
    }
    this.props.onChange(newValue)
  }

  onChangeOperator = (operator) => {
    const value = this.value
    const newValue = {
      ...value,
      operator
    }
    this.props.onChange(newValue)
  }

  render () {
    const { isReadOnly, name, fieldId, inputColumns, onSubmit } = this.props
    const { operator, filters } = this.value

    return (
      <React.Fragment>
        {filters.map((filter, index) => (
          <React.Fragment key={index}>
            <Filter
              isReadOnly={isReadOnly}
              name={`${name}[${index}]`}
              fieldId={`${fieldId}_${index}`}
              index={index}
              value={filter}
              inputColumns={inputColumns}
              onChange={this.onChangeFilter}
              onSubmit={onSubmit}
              onDelete={filters.length > 1 ? this.onDeleteFilter : null}
            />
            {index < filters.length - 1 ? (
              <FilterOperator
                isReadOnly={isReadOnly}
                name={`${name}[${index}][operator]`}
                fieldId={`${fieldId}_${index}_operator`}
                value={operator}
                onChange={this.onChangeOperator}
              />
            ) : (
              <AddFilter
                isReadOnly={isReadOnly}
                name={`${name}[operator]`}
                fieldId={`${fieldId}_operator`}
                operator={operator}
                nFilters={filters.length}
                onClickAddAnd={this.onClickAddAnd}
                onClickAddOr={this.onClickAddOr}
              />
            )}
          </React.Fragment>
        ))}
      </React.Fragment>
    )
  }
}
