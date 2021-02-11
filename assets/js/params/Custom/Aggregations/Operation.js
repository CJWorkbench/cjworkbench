import PropTypes from 'prop-types'
import { t } from '@lingui/macro'

export default function Operation ({ isReadOnly, name, value, onChange }) {
  // Mimic <MenuParam>'s HTML, but with string values. As of [2019-01-04],
  // <MenuParam> still only allows integer values, even though _every_ use
  // case warrants strings.
  return (
    <select
      className='operation'
      name={name}
      value={value}
      onChange={onChange}
      readOnly={isReadOnly}
    >
      <option value='size'>{t({ id: 'js.params.Custom.Aggregations.Operation.count.option', message: 'Count' })}</option>
      <option value='nunique'>{t({ id: 'js.params.Custom.Aggregations.Operation.countUnique.option', message: 'Count unique' })}</option>
      <option value='sum'>{t({ id: 'js.params.Custom.Aggregations.Operation.sum.option', message: 'Sum' })}</option>
      <option value='mean'>{t({ id: 'js.params.Custom.Aggregations.Operation.mean.option', message: 'Average (Mean)' })}</option>
      <option value='median'>{t({ id: 'js.params.Custom.Aggregations.Operation.median.option', message: 'Median' })}</option>
      <option value='min'>{t({ id: 'js.params.Custom.Aggregations.Operation.minimum.option', message: 'Minimum' })}</option>
      <option value='max'>{t({ id: 'js.params.Custom.Aggregations.Operation.maximum.option', message: 'Maximum' })}</option>
      <option value='first'>{t({ id: 'js.params.Custom.Aggregations.Operation.first.option', message: 'First' })}</option>
    </select>
  )
}
Operation.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
  onChange: PropTypes.func.isRequired // func(ev) => undefined
}
