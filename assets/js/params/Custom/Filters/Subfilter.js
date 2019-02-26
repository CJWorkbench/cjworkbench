import React from 'react'
import PropTypes from 'prop-types'
import { SubfilterPropType } from './PropTypes'
import Column from '../../Column'
import Condition from './Condition'
import SingleLineString from '../../String/SingleLineString'

const CaseSensitiveOperations = [
  'text_contains',
  'text_does_not_contain',
  'text_is_exactly',
  'text_contains_regex',
  'text_does_not_contain_regex',
  'text_is_exactly_regex',
]

export default class Subfilter extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired, // <input id=...>
    index: PropTypes.number.isRequired,
    value: SubfilterPropType.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onSubmit: PropTypes.func.isRequired,
    onDelete: PropTypes.func // (null if can't be deleted) func(index) => undefined
  }

  onDelete = () => {
    const { onDelete, index } = this.props
    onDelete(index)
  }

  onChangeColname = (colname) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, colname })
  }

  onChangeCondition = (condition) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, condition })
  }

  onChangeValue = (value) => {
    const { onChange, index } = this.props
    onChange(index, { ...this.props.value, value })
  }

  onChangeCaseSensitive = (ev) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, case_sensitive: ev.target.checked })
  }

  render () {
    const { isReadOnly, inputColumns, name, fieldId, index, value, onDelete, onSubmit } = this.props
    const column = (inputColumns || []).find(c => c.name === value.colname) || null
    const needValue = column !== null && (
      value.condition !== 'cell_is_empty' && value.condition !== 'cell_is_not_empty'
    )

    return (
      <div className='subfilter'>
        <Column
          isReadOnly={isReadOnly}
          name={`${name}[colname]`}
          fieldId={`${fieldId}_colname`}
          value={value.colname}
          placeholder='Select column'
          inputColumns={inputColumns}
          onChange={this.onChangeColname}
        />
        {column ? (
          <Condition
            isReadOnly={isReadOnly}
            name={`${name}[condition]`}
            fieldId={`${fieldId}_condition`}
            value={value.condition}
            dtype={column.type}
            onChange={this.onChangeCondition}
          />
        ) : null}
        {needValue ? (
          <div className='value'>
            <SingleLineString
              isReadOnly={isReadOnly}
              label=''
              name={`${name}[value]`}
              fieldId={`${fieldId}_value`}
              placeholder='Value'
              value={value.value}
              upstreamValue={value.value}
              onChange={this.onChangeValue}
              onSubmit={onSubmit}
            />
          </div>
        ) : null}
        {(column && CaseSensitiveOperations.includes(value.condition)) ? (
          <label
            className='case-sensitive'
          >
            <input
              type='checkbox'
              readOnly={isReadOnly}
              name={`${name}[case_sensitive]`}
              id={`${fieldId}_case_sensitive`}
              checked={value.case_sensitive}
              onChange={this.onChangeCaseSensitive}
            />
            Match case
          </label>
        ) : null}
        {onDelete ? (
          <button
            type='button'
            className='delete'
            onClick={this.onDelete}
          >
            <i className='icon-close' />
          </button>
        ) : null}
      </div>
    )
  }
}
