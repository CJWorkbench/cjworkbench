import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

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
      <option value='size'><Trans id='js.params.Custom.Aggregations.Operation.count.option'>Count</Trans></option>
      <option value='nunique'><Trans id='js.params.Custom.Aggregations.Operation.countUnique.option'>Count unique</Trans></option>
      <option value='sum'><Trans id='js.params.Custom.Aggregations.Operation.sum.option'>Sum</Trans></option>
      <option value='mean'><Trans id='js.params.Custom.Aggregations.Operation.mean.option'>Average (Mean)</Trans></option>
      <option value='median'><Trans id='js.params.Custom.Aggregations.Operation.median.option'>Median</Trans></option>
      <option value='min'><Trans id='js.params.Custom.Aggregations.Operation.minimum.option'>Minimum</Trans></option>
      <option value='max'><Trans id='js.params.Custom.Aggregations.Operation.maximum.option'>Maximum</Trans></option>
      <option value='first'><Trans id='js.params.Custom.Aggregations.Operation.first.option'>First</Trans></option>
    </select>
  )
}
Operation.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
  onChange: PropTypes.func.isRequired // func(ev) => undefined
}
