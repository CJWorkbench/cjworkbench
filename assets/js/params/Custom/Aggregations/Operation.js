import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export function Operation ({ i18n, isReadOnly, name, value, onChange }) {
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
      <option value='size'>{i18n._(t('js.params.Custom.Aggregations.Operation.count.option')`Count`)}</option>
      <option value='nunique'>{i18n._(t('js.params.Custom.Aggregations.Operation.countUnique.option')`Count unique`)}</option>
      <option value='sum'>{i18n._(t('js.params.Custom.Aggregations.Operation.sum.option')`Sum`)}</option>
      <option value='mean'>{i18n._(t('js.params.Custom.Aggregations.Operation.mean.option')`Average (Mean)`)}</option>
      <option value='median'>{i18n._(t('js.params.Custom.Aggregations.Operation.median.option')`Median`)}</option>
      <option value='min'>{i18n._(t('js.params.Custom.Aggregations.Operation.minimum.option')`Minimum`)}</option>
      <option value='max'>{i18n._(t('js.params.Custom.Aggregations.Operation.maximum.option')`Maximum`)}</option>
      <option value='first'>{i18n._(t('js.params.Custom.Aggregations.Operation.first.option')`First`)}</option>
    </select>
  )
}
Operation.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'median', 'min', 'max', 'first']).isRequired,
  onChange: PropTypes.func.isRequired, // func(ev) => undefined
  i18n: PropTypes.object
}

export default withI18n()(Operation)
