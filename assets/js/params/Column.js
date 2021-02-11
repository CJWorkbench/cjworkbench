// Pick a single column
import PropTypes from 'prop-types'
import ReactSelect from './common/react-select'
import { MaybeLabel } from './util'
import { t } from '@lingui/macro'

export default function ColumnParam (props) {
  const { inputColumns, isReadOnly, placeholder, fieldId, label, name, value, onChange } = props
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
    <>
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
        placeholder={placeholder || t({ id: 'js.params.Column.select.placeholder', message: 'Select' })}
      />
    </>
  )
}
ColumnParam.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.string, // or null
  placeholder: PropTypes.string, // default 'Select'
  isReadOnly: PropTypes.bool.isRequired,
  inputColumns: PropTypes.arrayOf(PropTypes.shape({
    name: PropTypes.string.isRequired
  })), // or null if unknown
  onChange: PropTypes.func.isRequired // func(colnameOrNull) => undefined
}
