import { PureComponent, Fragment } from 'react'
import PropTypes from 'prop-types'
import { ConditionPropType } from './PropTypes'
import Group from './Group'
import AndOr from './AndOr'
import AddButton from './AddButton'

const DefaultConditionLevel2 = {
  operation: '',
  column: '',
  value: '',
  isCaseSensitive: false,
  isRegex: false
}
const DefaultConditionLevel1 = {
  operation: 'and',
  conditions: [DefaultConditionLevel2]
}
const DefaultValue = {
  operation: 'and',
  conditions: [DefaultConditionLevel1]
}

export default class Condition extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    value: ConditionPropType.isRequired,
    inputColumns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
      })
    ), // or null if unknown
    onChange: PropTypes.func.isRequired,
    onSubmit: PropTypes.func.isRequired
  }

  get value () {
    const { value } = this.props

    if (!value || !value.conditions.length) {
      return DefaultValue
    }

    return value
  }

  addOperator (operator) {
    // Add a DefaultGroup to the end of the groups list
    const newValue = {
      operation: operator,
      conditions: [...this.value.conditions, DefaultConditionLevel1]
    }
    this.props.onChange(newValue)
  }

  handleClickAddAnd = () => this.addOperator('and')
  handleClickAddOr = () => this.addOperator('or')

  handleDeleteCondition = index => {
    const value = this.value
    const conditions = value.conditions.slice() // copy: we'll mutate it
    conditions.splice(index, 1)
    const newValue = { ...value, conditions }
    this.props.onChange(newValue)
  }

  handleChangeCondition = (index, condition) => {
    const value = this.value
    const conditions = value.conditions.slice() // copy: we'll mutate it
    conditions[index] = condition
    const newValue = { ...value, conditions }
    this.props.onChange(newValue)
  }

  handleChangeAndOr = operation => {
    const newValue = { ...this.value, operation }
    this.props.onChange(newValue)
  }

  render () {
    const { isReadOnly, name, fieldId, inputColumns, onSubmit } = this.props
    const { operation, conditions } = this.value

    return conditions.map((filter, index) => (
      <Fragment key={index}>
        <Group
          isReadOnly={isReadOnly}
          name={`${name}[${index}]`}
          fieldId={`${fieldId}_${index}`}
          index={index}
          value={filter}
          inputColumns={inputColumns}
          onChange={this.handleChangeCondition}
          onSubmit={onSubmit}
          onDelete={conditions.length > 1 ? this.handleDeleteCondition : null}
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
              className='add-group'
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
    ))
  }
}
