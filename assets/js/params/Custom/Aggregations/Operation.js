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
      {<option value='size'><Trans id='workflow.count'>Count</Trans></option>}
      {<option value='nunique'><Trans id='workflow.countunique'>Count unique</Trans></option>}
      {<option value='sum'><Trans id='workflow.sum'>Sum</Trans></option>}
      {<option value='mean'><Trans id='workflow.Averagemean'>Average (Mean)</Trans></option>}
      {<option value='median'><Trans id='workflow.median'>Median</Trans></option>}
      {<option value='min'><Trans id='workflow.Minimum'>Minimum</Trans></option>}
      {<option value='max'><Trans id='workflow.maximum'>Maximum</Trans></option>}
      {<option value='first'><Trans id='workflow.first'>First</Trans></option>}
    </select>
  )
}
Operation.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
  onChange: PropTypes.func.isRequired // func(ev) => undefined
}
