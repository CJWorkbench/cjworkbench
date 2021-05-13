import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import Checkbox from '../Checkbox'
import Multicolumn from '../Multicolumn'

export default function Groups (props) {
  const { isReadOnly, name, fieldId, value, inputColumns, onChange } = props

  const handleChangeColnames = React.useCallback(
    colnames => { onChange({ ...value, colnames }) },
    [onChange, value]
  )

  const handleChangeGroupDates = React.useCallback(
    bool => { onChange({ ...value, group_dates: bool }) },
    [onChange, value]
  )

  // TODO nix this custom param; use regular params instead
  // In the meantime, this className="param param-checkbox" stuff should give
  // the exact same style.

  return (
    <>
      <div className='param param-multicolumn'>
        <Multicolumn
          isReadOnly={isReadOnly}
          name={`${name}[colnames]`}
          fieldId={`${fieldId}_colnames`}
          upstreamValue={value.colnames}
          value={value.colnames}
          inputColumns={inputColumns}
          onChange={handleChangeColnames}
        />
      </div>
      <div className='param param-checkbox'>
        <Checkbox
          isReadOnly={isReadOnly}
          label={t({ id: 'js.params.Custom.Groups.groupDates', message: 'Help with dates' })}
          name={`${name}[group_dates]`}
          fieldId={`${fieldId}_group_dates`}
          value={value.group_dates}
          onChange={handleChangeGroupDates}
        />
      </div>
    </>
  )
}
Groups.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // for <input> names
  fieldId: PropTypes.string.isRequired, // <input id="...">
  value: PropTypes.shape({
    colnames: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
    group_dates: PropTypes.bool.isRequired
  }).isRequired,
  inputColumns: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['date', 'text', 'number', 'timestamp']).isRequired
    })
  ), // or null if unknown
  onChange: PropTypes.func.isRequired // func(value) => undefined
}
