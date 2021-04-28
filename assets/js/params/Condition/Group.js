import { PureComponent, Fragment } from 'react'
import PropTypes from 'prop-types'
import { GroupPropType, ComparisonDefaultProps } from './PropTypes'
import Comparison from './Comparison'
import AddButton from './AddButton'
import AndOr from './AndOr'
import { Trans } from '@lingui/macro'

export default class Group extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    index: PropTypes.number.isRequired,
    value: GroupPropType.isRequired,
    inputColumns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
      })
    ), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onSubmit: PropTypes.func.isRequired,
    onDelete: PropTypes.func // (null if can't be deleted) func(index) => undefined
  }

  handleChangeAndOr = operation => {
    const { value, onChange, index } = this.props
    onChange(index, { ...value, operation })
  }

  handleChangeComparison = (index, condition) => {
    const { value, onChange, index: ourIndex } = this.props
    const conditions = value.conditions.slice() // copy: we'll mutate it
    conditions[index] = condition
    onChange(ourIndex, { ...value, conditions })
  }

  addCondition = operation => {
    const { value, onChange, index } = this.props
    onChange(index, {
      ...value,
      operation,
      conditions: [...value.conditions, ComparisonDefaultProps]
    })
  }

  handleClickAddAnd = () => this.addCondition('and')
  handleClickAddOr = () => this.addCondition('or')

  handleDeleteCondition = conditionIndex => {
    const { value, onChange, index } = this.props
    const conditions = value.conditions.slice() // copy: we'll mutate it
    conditions.splice(conditionIndex, 1)
    onChange(index, { ...value, conditions })
  }

  handleDelete = () => {
    const { onDelete, index } = this.props
    onDelete(index)
  }

  render () {
    const {
      isReadOnly,
      inputColumns,
      onSubmit,
      name,
      fieldId,
      value,
      onDelete
    } = this.props
    const { operation, conditions } = value

    return (
      <div className='group'>
        <div className='group-heading'>
          <h5>
            <Trans id='js.params.Condition.Group.heading.title'>If</Trans>
          </h5>
          {onDelete
            ? (
              <button
                type='button'
                className='delete'
                onClick={this.handleDelete}
              >
                <i className='icon-close' />
              </button>
              )
            : null}
        </div>
        {conditions.map((comparison, index) => (
          <Fragment key={index}>
            <Comparison
              isReadOnly={isReadOnly}
              name={`${name}[${index}]`}
              fieldId={`${fieldId}_${index}`}
              index={index}
              value={comparison}
              inputColumns={inputColumns}
              onChange={this.handleChangeComparison}
              onSubmit={onSubmit}
              onDelete={
                conditions.length > 1 ? this.handleDeleteCondition : null
              }
            />
            {index < conditions.length - 1
              ? (
                <AndOr
                  isReadOnly={isReadOnly}
                  name={`${name}[${index}][operation]`}
                  fieldId={`${fieldId}_${index}_operation`}
                  value={operation}
                  onChange={this.handleChangeAndOr}
                />
                )
              : (
                <AddButton
                  className='add-comparison'
                  isReadOnly={isReadOnly}
                  name={`${name}[operation]`}
                  fieldId={`${fieldId}_operation`}
                  operation={operation}
                  isFirst={conditions.length <= 1}
                  onClickAddAnd={this.handleClickAddAnd}
                  onClickAddOr={this.handleClickAddOr}
                />
                )}
          </Fragment>
        ))}
      </div>
    )
  }
}
