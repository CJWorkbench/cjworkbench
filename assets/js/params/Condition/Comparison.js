import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import { ComparisonPropType } from './PropTypes'
import Column from '../Column'
import ComparisonOperator from './ComparisonOperator'
import SingleLineString from '../String/SingleLineString'
import { t, Trans } from '@lingui/macro'

export default class Comparison extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    index: PropTypes.number.isRequired,
    value: ComparisonPropType.isRequired,
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

  handleDelete = () => {
    const { onDelete, index } = this.props
    onDelete(index)
  }

  handleChangeColumn = column => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, column })
  }

  handleChangeOperation = operation => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, operation })
  }

  handleChangeValue = value => {
    const { onChange, index } = this.props
    onChange(index, { ...this.props.value, value })
  }

  handleChangeCaseSensitive = ev => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, isCaseSensitive: ev.target.checked })
  }

  handleChangeRegex = ev => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, isRegex: ev.target.checked })
  }

  render () {
    const {
      isReadOnly,
      inputColumns,
      name,
      fieldId,
      value,
      onDelete,
      onSubmit
    } = this.props
    const column =
      (inputColumns || []).find(c => c.name === value.column) || null
    const isText = column !== null && value.operation.startsWith('text_')
    const needValue = column !== null && !value.operation.startsWith('cell_')

    return (
      <div className='comparison'>
        <Column
          isReadOnly={isReadOnly}
          name={`${name}[column]`}
          fieldId={`${fieldId}_column`}
          value={value.column}
          placeholder={t({
            id: 'js.params.Condition.Comparison.column.placeholder',
            message: 'Select column'
          })}
          inputColumns={inputColumns}
          onChange={this.handleChangeColumn}
        />
        {column
          ? (
            <ComparisonOperator
              isReadOnly={isReadOnly}
              name={`${name}[operation]`}
              fieldId={`${fieldId}_condition`}
              value={value.operation}
              dtype={column.type}
              onChange={this.handleChangeOperation}
            />
            )
          : null}
        {needValue
          ? (
            <div className='value'>
              <SingleLineString
                isReadOnly={isReadOnly}
                label=''
                name={`${name}[value]`}
                fieldId={`${fieldId}_value`}
                placeholder={t({
                  id: 'js.params.Condition.Comparison.value.placeholder',
                  message: 'Value'
                })}
                value={value.value}
                upstreamValue={value.value}
                onChange={this.handleChangeValue}
                onSubmit={onSubmit}
              />
            </div>
            )
          : null}
        {column && isText
          ? (
            <div className='text-options'>
              <label className='case-sensitive'>
                <input
                  type='checkbox'
                  readOnly={isReadOnly}
                  name={`${name}[case_sensitive]`}
                  id={`${fieldId}_case_sensitive`}
                  checked={value.isCaseSensitive || false}
                  onChange={this.handleChangeCaseSensitive}
                />
                <Trans id='js.params.Condition.Comparison.caseSensitive'>
                  Case-sensitive
                </Trans>
              </label>
              <label className='regex'>
                <input
                  type='checkbox'
                  readOnly={isReadOnly}
                  name={`${name}[regex]`}
                  id={`${fieldId}_regex`}
                  checked={value.isRegex || false}
                  onChange={this.handleChangeRegex}
                />
                <Trans id='js.params.Condition.Comparison.regex'>
                  Regular expression
                </Trans>
              </label>
            </div>
            )
          : null}
        {onDelete
          ? (
            <button type='button' className='delete' onClick={this.handleDelete}>
              <i className='icon-close' />
            </button>
            )
          : null}
      </div>
    )
  }
}
