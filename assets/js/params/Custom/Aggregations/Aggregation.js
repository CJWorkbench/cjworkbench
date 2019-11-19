import React from 'react'
import PropTypes from 'prop-types'
import Operation from './Operation'
import ColumnParam from '../../Column'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

class Aggregation extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    fieldId: PropTypes.string.isRequired, // for <input id=...>
    index: PropTypes.number.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onDelete: PropTypes.func, // func(index) => undefined, or null if delete not allowed
    operation: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
    colname: PropTypes.string.isRequired,
    outname: PropTypes.string.isRequired, // may be empty
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    })
  }

  handleChangeOperation = (ev) => {
    const { colname, index, outname, onChange } = this.props
    onChange(index, { colname, outname, operation: ev.target.value })
  }

  handleChangeColname = (colnameOrNull) => {
    const { outname, operation, index, onChange } = this.props
    onChange(index, { outname, operation, colname: (colnameOrNull || '') })
  }

  handleChangeOutname = (ev) => {
    const { colname, operation, index, onChange } = this.props
    onChange(index, { colname, operation, outname: ev.target.value })
  }

  handleClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  get placeholder () {
    // Duplicated from grroupby/groupby.py
    const { operation, colname, i18n } = this.props

    if (operation === 'size') return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.size')`Group Size`)

    if (colname === '') {
      // reduce clutter -- groupby.py won't add this operation anyway
      return ''
    }

    switch (operation) {
      case 'nunique': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.nunique')`Unique count of ${colname}`)
      case 'sum': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.sum')`Sum of ${colname}`)
      case 'mean': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.mean')`Average of ${colname}`)
      case 'median': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.median')`Median of ${colname}`)
      case 'min': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.min')`Minimum of ${colname}`)
      case 'max': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.max')`Maximum of ${colname}`)
      case 'first': return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.first')`First of ${colname}`)
      default: return i18n._(t('js.params.Custom.Aggregations.Aggregation.placeholder.default')`(default)`)
    }
  }

  render () {
    const { name, fieldId, onDelete, operation, colname, outname, inputColumns, isReadOnly, i18n } = this.props

    return (
      <li className='aggregation'>
        <Operation
          isReadOnly={isReadOnly}
          name={`${name}[operation]`}
          fieldId={`${fieldId}_operation`}
          value={operation}
          onChange={this.handleChangeOperation}
        />
        {operation === 'size' ? null : (
          <ColumnParam
            name={`${name}[colname]`}
            fieldId={`${fieldId}_colname`}
            value={colname}
            prompt={i18n._(t('js.params.custom.Aggregations.Aggregation.ColumnParam.prompt')`Select a column`)}
            isReadOnly={isReadOnly}
            inputColumns={inputColumns}
            onChange={this.handleChangeColname}
          />
        )}
        <label className='outname'>
          <span className='name'><Trans id='js.params.custom.Aggregations.Aggregation.outname'>Name</Trans></span>
          <input
            className='outname'
            name={`${name}[outname]`}
            id={`${fieldId}_outname`}
            value={outname}
            onChange={this.handleChangeOutname}
            placeholder={this.placeholder}
          />
        </label>
        {(onDelete && !isReadOnly) ? (
          <div className='delete'>
            <button
              type='button'
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

export default withI18n()(Aggregation)
