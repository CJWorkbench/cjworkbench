import React from 'react'
import PropTypes from 'prop-types'
import { SubfilterPropType } from './PropTypes'
import Column from '../../Column'
import Condition from './Condition'
import SingleLineString from '../../String/SingleLineString'
import { withI18n } from '@lingui/react'
import { t, Trans } from '@lingui/macro'

const CaseSensitiveOperations = [
  'text_contains',
  'text_does_not_contain',
  'text_is_exactly',
  'text_is_not_exactly',
  'text_contains_regex',
  'text_does_not_contain_regex',
  'text_is_exactly_regex'
]

const ConditionsNeedingNoValue = [
  'cell_is_empty',
  'cell_is_not_empty',
  'cell_is_empty_str_or_null',
  'cell_is_not_empty_str_or_null'
]

class Subfilter extends React.PureComponent {
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

  handleDelete = () => {
    const { onDelete, index } = this.props
    onDelete(index)
  }

  handleChangeColname = (colname) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, colname })
  }

  handleChangeCondition = (condition) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, condition })
  }

  handleChangeValue = (value) => {
    const { onChange, index } = this.props
    onChange(index, { ...this.props.value, value })
  }

  handleChangeCaseSensitive = (ev) => {
    const { onChange, index, value } = this.props
    onChange(index, { ...value, case_sensitive: ev.target.checked })
  }

  render () {
    const { isReadOnly, inputColumns, name, fieldId, value, onDelete, onSubmit } = this.props
    const column = (inputColumns || []).find(c => c.name === value.colname) || null
    const needValue = column !== null && !ConditionsNeedingNoValue.includes(value.condition)

    return (
      <div className='subfilter'>
        <Column
          isReadOnly={isReadOnly}
          name={`${name}[colname]`}
          fieldId={`${fieldId}_colname`}
          value={value.colname}
          placeholder={this.props.i18n._(t('js.params.Custom.Filters.Subfilter.Column.placeholder')`Select column`)}
          inputColumns={inputColumns}
          onChange={this.handleChangeColname}
        />
        {column ? (
          <Condition
            isReadOnly={isReadOnly}
            name={`${name}[condition]`}
            fieldId={`${fieldId}_condition`}
            value={value.condition}
            dtype={column.type}
            onChange={this.handleChangeCondition}
          />
        ) : null}
        {needValue ? (
          <div className='value'>
            <SingleLineString
              isReadOnly={isReadOnly}
              label=''
              name={`${name}[value]`}
              fieldId={`${fieldId}_value`}
              placeholder={this.props.i18n._(t('js.params.Custom.Filters.Subfilter.SingleLineString.placeholder')`Value`)}
              value={value.value}
              upstreamValue={value.value}
              onChange={this.handleChangeValue}
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
              onChange={this.handleChangeCaseSensitive}
            />
            <Trans id='js.params.Custom.Filters.Subfilter.matchCase'>Match case</Trans>
          </label>
        ) : null}
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
    )
  }
}

export default withI18n()(Subfilter)
