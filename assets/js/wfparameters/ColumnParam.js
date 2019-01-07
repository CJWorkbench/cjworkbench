// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'
import Select from 'react-select'

export default class ColumnParam extends React.PureComponent {
  static propTypes = {
    className: PropTypes.string, // or null
    name: PropTypes.string.isRequired,
    value: PropTypes.string, // or null
    prompt: PropTypes.string, // default 'Select'
    isReadOnly: PropTypes.bool.isRequired,
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func(colnameOrNull) => undefined
  }

  onChange = (ev) => {
    this.props.onChange(ev.value || null)
  }

  render() {
    const { allColumns, isReadOnly, prompt, name, value, className } = this.props
    const isLoading = (allColumns === null)

    // Set dropdown list to 1 option of 'loading' as we wait. When clicked, onChange passes null to callback
    const columnOptions = (allColumns || []).map(column => (
      {
        label: column.name,
        value: column.name
      }
    ))
    const selectedOption = columnOptions.find(c => c.value === value)

    // Keeping classNamePrefix since CSS definitions already exist
    return (
      <div className={`column-param ${className || ''}`}>
        <Select
          name={name}
          key={value}
          options={columnOptions}
          value={selectedOption}
          isLoading={isLoading}
          className='react-select'
          classNamePrefix='react-select'
          menuPortalTarget={document.body}
          onChange={this.onChange}
          isClearable={false}
          isDisabled={this.props.isReadOnly}
          placeholder={prompt || 'Select'}
        />
      </div>
    )
  }
}
