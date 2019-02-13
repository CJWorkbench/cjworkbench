// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'
import ReactSelect from './common/react-select'
import { MaybeLabel } from './util'

export default class ColumnParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string, // or null
    placeholder: PropTypes.string, // default 'Select'
    isReadOnly: PropTypes.bool.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func(colnameOrNull) => undefined
  }

  render() {
    const { inputColumns, isReadOnly, placeholder, fieldId, label, name, value, onChange } = this.props
    const isLoading = (inputColumns === null)

    // Set dropdown list to 1 option of 'loading' as we wait. When clicked, onChange passes null to callback
    const columnOptions = (inputColumns || []).map(column => (
      {
        label: column.name,
        value: column.name
      }
    ))

    // Keeping classNamePrefix since CSS definitions already exist
    return (
      <React.Fragment>
        <MaybeLabel fieldId={fieldId} label={label} />
        <ReactSelect
          name={name}
          key={value}
          inputId={fieldId}
          options={columnOptions}
          value={value}
          isLoading={isLoading}
          onChange={onChange}
          isReadOnly={isReadOnly}
          placeholder={placeholder || 'Select'}
        />
      </React.Fragment>
    )
  }
}
