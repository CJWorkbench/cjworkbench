import React from 'react'

export function generateFieldId (wfModuleId, name) {
  const cleanName = name.replace(/[^0-9a-zA-Z_-]/g, '-')
  return `field-${wfModuleId}-${cleanName}`
}

/**
 * An HTML <label> for use in params, or `null` if `label` is empty.
 *
 * Use the `fieldId` that comes with the `Param`.
 */
export function MaybeLabel ({ fieldId, label }) {
  if (!label) return null
  return (
    <label htmlFor={fieldId}>
      {label}
    </label>
  )
}

/**
 * Higher-order component: makes its `value` JSON where it would otherwise be String
 *
 * Historically, Workbench only stored strings; so many components generate
 * String values that are actually JSON, encoded. (They're all Array or Object
 * values.)
 *
 * This will JSON-parse `value` and JSON-stringify in `onChange`.
 */
export function withJsonStringValues(WrappedComponent, defaultValue) {
  return (props) => {
    const { value, upstreamValue, onChange } = props
    let realValue, realUpstreamValue

    try {
      realValue = JSON.parse(value)
    } catch {
      realValue = defaultValue
    }

    try {
      realUpstreamValue = JSON.parse(upstreamValue)
    } catch {
      realUpstreamValue = defaultValue
    }

    const onChangeJson = (value) => onChange(JSON.stringify(value))

    return (
      <WrappedComponent
        {...props}
        value={realValue}
        upstreamValue={realUpstreamValue}
        onChange={onChangeJson}
      />
    )
  }
}


// Takes the server-generated param_field spec, which is basically just the module YAML, and turns it into
// props for Param, which have been sanitized/transformed
export function paramFieldToParamProps (field) {
  return {
    name: field.idName, // NOTE! idName on server is called name here, ala HTML form terminology
    label: field.name, // similarly, name is called label here
    type: field.type,
    enumOptions: field.options, // may be undefined
    isMultiline: field.multiline || false,
    placeholder: field.placeholder || '',
    visibleIf: field.visibleIf, // may be null
    childParameters: field.childParameters, // may be undefined
    childDefault: field.childDefault // may be undefined
  }
}
