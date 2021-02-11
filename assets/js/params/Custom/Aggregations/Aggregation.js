import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import Operation from './Operation'
import ColumnParam from '../../Column'
import { Trans, t } from '@lingui/macro'

export default class Aggregation extends PureComponent {
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
    outname: PropTypes.string.isRequired // may be empty
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
    // Duplicated from groupby/groupby.py
    const { operation, colname } = this.props

    if (operation === 'size') {
      return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.size', message: 'Group Size' })
    }

    if (colname === '') {
      // reduce clutter -- groupby.py won't add this operation anyway
      return ''
    }

    switch (operation) {
      case 'nunique': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.nunique', message: 'Unique count of {colname}', values: { colname } })
      case 'sum': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.sum', message: 'Sum of {colname}', values: { colname } })
      case 'mean': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.mean', message: 'Average of {colname}', values: { colname } })
      case 'median': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.median', message: 'Median of {colname}', values: { colname } })
      case 'min': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.min', message: 'Minimum of {colname}', values: { colname } })
      case 'max': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.max', message: 'Maximum of {colname}', values: { colname } })
      case 'first': return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.first', message: 'First of {colname}', values: { colname } })
      default: return t({ id: 'js.params.Custom.Aggregations.Aggregation.placeholder.default', message: '(default, message: ' })
    }
  }

  render () {
    const { name, fieldId, onDelete, operation, colname, outname, inputColumns, isReadOnly } = this.props

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
            prompt={t({ id: 'js.params.custom.Aggregations.Aggregation.ColumnParam.prompt', message: 'Select a column' })}
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
