import React from 'react'
import PropTypes from 'prop-types'
import { FilterPropType } from './PropTypes'
import Subfilter from './Subfilter'
import AddFilter from './AddFilter'
import FilterOperator from './FilterOperator'
import { Trans } from '@lingui/macro'

const DefaultSubfilter = {
  colname: '',
  condition: '',
  value: '',
  case_sensitive: false
}

export default class Filter extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    index: PropTypes.number.isRequired,
    value: FilterPropType.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onSubmit: PropTypes.func.isRequired,
    onDelete: PropTypes.func // (null if can't be deleted) func(index) => undefined
  }

  handleChangeOperator = (operator) => {
    const { value, onChange, index } = this.props
    onChange(index, { ...value, operator })
  }

  handleChangeSubfilter = (subfilterIndex, subfilter) => {
    const { value, onChange, index } = this.props
    const newSubfilters = value.subfilters.slice()
    newSubfilters[subfilterIndex] = subfilter
    onChange(index, { ...value, subfilters: newSubfilters })
  }

  addSubfilter = (operator) => {
    const { value, onChange, index } = this.props
    onChange(index, {
      ...value,
      operator,
      subfilters: [...value.subfilters, DefaultSubfilter]
    })
  }

  handleClickAddAnd = () => this.addSubfilter('and')
  handleClickAddOr = () => this.addSubfilter('or')

  handleDeleteSubfilter = (subfilterIndex) => {
    const { value, onChange, index } = this.props
    const newSubfilters = value.subfilters.slice()
    newSubfilters.splice(subfilterIndex, 1)
    onChange(index, { ...value, subfilters: newSubfilters })
  }

  handleDelete = () => {
    const { onDelete, index } = this.props
    onDelete(index)
  }

  render () {
    const { isReadOnly, inputColumns, onSubmit, name, fieldId, value, onDelete } = this.props
    const { operator, subfilters } = value

    return (
      <div className='filter'>
        <div className='filter-heading'>
          <h5><Trans id='js.params.custom.Filters.Filter.heading.title'>If</Trans></h5>
          {onDelete ? (
            <button
              type='button'
              className='delete'
              onClick={this.handleDelete}
            >
              <i className='icon-close' />
            </button>
          ) : null}
        </div>
        {subfilters.map((subfilter, index) => (
          <React.Fragment key={index}>
            <Subfilter
              isReadOnly={isReadOnly}
              name={`${name}[${index}]`}
              fieldId={`${fieldId}_${index}`}
              index={index}
              value={subfilter}
              inputColumns={inputColumns}
              onChange={this.handleChangeSubfilter}
              onSubmit={onSubmit}
              onDelete={subfilters.length > 1 ? this.handleDeleteSubfilter : null}
            />
            {index < subfilters.length - 1 ? (
              <FilterOperator
                isReadOnly={isReadOnly}
                name={`${name}[${index}][operator]`}
                fieldId={`${fieldId}_${index}_operator`}
                value={operator}
                onChange={this.handleChangeOperator}
              />
            ) : (
              <AddFilter
                isReadOnly={isReadOnly}
                name={`${name}[operator]`}
                fieldId={`${fieldId}_operator`}
                operator={operator}
                nFilters={subfilters.length}
                onClickAddAnd={this.handleClickAddAnd}
                onClickAddOr={this.handleClickAddOr}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    )
  }
}
