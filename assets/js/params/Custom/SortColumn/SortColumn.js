import React from 'react'
import PropTypes from 'prop-types'
import ColumnParam from '../../Column'
import RadioParam from '../../Radio.js'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const AscendingParam = withI18n()(function ({ i18n, ...props }) {
  const AscendingParamOptions = [
    { value: true, label: i18n._(t('js.params.Custom.SortColumn.AscendingParam.ascending')`Ascending`) },
    { value: false, label: i18n._(t('js.params.Custom.SortColumn.AscendingParam.descending')`Descending`) }
  ]

  return (
    // TODO find a better way to simulate .param-radio?
    <div className='param param-radio'>
      <RadioParam
        enumOptions={AscendingParamOptions}
        {...props}
      />
    </div>
  )
})
AscendingParam.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // for <input name=...>
  fieldId: PropTypes.string.isRequired, // <input id=...>
  onChange: PropTypes.func.isRequired, // func(index, value) => undefined
  value: PropTypes.bool.isRequired,
  i18n: PropTypes.shape({
    // i18n object injected by LinguiJS withI18n()
    _: PropTypes.func.isRequired
  })
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

  handleChangeIsAscending = (isAscending) => {
    const { index, value: { colname }, onChange } = this.props
    onChange(index, { colname, is_ascending: isAscending })
  }

  handleChangeColname = (colnameOrNull) => {
    const { index, value, onChange } = this.props
    onChange(index, { is_ascending: value.is_ascending, colname: (colnameOrNull || '') })
  }

  handleClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  render () {
    const { index, value, name, fieldId, onDelete, isReadOnly, inputColumns } = this.props
    const label = index === 0 ? <Trans id='js.params.Custom.SortColumn.by.label'>By</Trans> : <Trans id='js.params.Custom.SortColumn.thenBy.label'>Then by</Trans>

    return (
      <li>
        <ColumnParam
          label={label}
          key={index}
          name={`${name}[colname]`}
          fieldId={`${fieldId}_colname`}
          value={value.colname}
          prompt='Select a column'
          isReadOnly={isReadOnly}
          inputColumns={inputColumns}
          onChange={this.handleChangeColname}
        />
        <AscendingParam
          name={`${name}[is_ascending]`}
          fieldId={`${fieldId}_is_ascending`}
          value={value.is_ascending}
          isReadOnly={isReadOnly}
          onChange={this.handleChangeIsAscending}
        />
        {(onDelete && !isReadOnly) ? (
          <div className='delete'>
            <button
              className='delete'
              name={`${name}[delete]`}
              onClick={this.handleClickDelete}
            >
              <i className='icon-close' />
            </button>
          </div>
        ) : null}
      </li>
    )
  }
}
