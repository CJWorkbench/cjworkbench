// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'
import Select from 'react-select'

export default class ColumnParam extends React.PureComponent {
  static propTypes = {
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
    const {allColumns, prompt, value} = this.props
    let className = "react-select"
    let columnOptions

    // Set dropdown list to 1 option of 'loading' as we wait. When clicked, onChange passes null to callback
    if (allColumns === null) {
      className += ' loading'
      columnOptions = [
        {
          label: 'loading',
          value: ''
        }
      ]}
    else {
      columnOptions = allColumns.map(column => (
        {
          label: column.name,
          value: column.name
        }
      ))
    }
    // Keeping classNamePrefix since CSS definitions already exist
    return (
      <Select
        name={this.props.name}
        options={columnOptions}
        className={className}
        classNamePrefix="react-select"
        menuPortalTarget={document.body}
        onChange={this.onChange}
        isClearable={true}
        isDisabled={this.props.isReadOnly}
        placeholder={prompt || 'Select'}
      />
    )
  }
}
