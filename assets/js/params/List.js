import React from 'react'
import PropTypes from 'prop-types'
import Param from './Param'
import { paramFieldToParamProps } from './util'

// A single repetition of the set of parameters defined by param_fields.child_parameters
// which is ultimately set by the 'parameters' key of the 'list' parameter type in the module YAML
class ChildForm extends React.PureComponent {
  static propTypes = {
    childParameters: PropTypes.object.isRequired,
    value: PropTypes.object.isRequired,
    commonProps: PropTypes.object.isRequired,
    index: PropTypes.number.isRequired, // passed in rather than parent needing to create a closure, which causes re-render
    onChange: PropTypes.func.isRequired // func(index, value of all form fields) => undefined
  }

  onChangeParam = (idName, childParamValue) => {
    const { value, index, onChange } = this.props
    onChange(index, {
      ...value,
      [idName]: childParamValue
    })
  }

  render () {
    const { childParameters, value, commonProps } = this.props
    return (
      <div className='list-child-form'>
        {childParameters.map(childParameter => (
          <Param
            {...commonProps}
            {...paramFieldToParamProps(childParameter)}
            value={value[childParameter.id_name]}
            onChange={this.onChangeParam}
          />
        ))}
      </div>
    )
  }
}

// Multiple repetitions of a set of parameters
export default class List extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    label: PropTypes.string.isRequired,
    fieldId: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // func(list) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    name: PropTypes.string.isRequired,
    upstreamValue: PropTypes.array.isRequired, // sometimes empty string
    value: PropTypes.array.isRequired,
    childParameters: PropTypes.array.isRequired,
    childDefault: PropTypes.object.isRequired
  }

  /**
   * List of child parameter values, for all repetitions, or default (one repetition) if empty
   */
  get value () {
    const actual = this.props.value
    if (actual.length === 0) {
      return [ this.props.childDefault ]
    } else {
      return actual
    }
  }

  onChangeChildFormValue = (index, childFormValue) => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue[index] = childFormValue // may append an element
    onChange(newValue)
  }

  // onDeleteAggregation = (index) => {
  //   const { onChange, isReadOnly } = this.props
  //   if (isReadOnly) return
  //   const newValue = this.value.slice()
  //   newValue.splice(index, 1)
  //   onChange(newValue)
  // }

  onAdd = () => {
    const { onChange, isReadOnly, childDefault } = this.props
    if (isReadOnly) return
    const newValue = [ ...this.value, childDefault ]
    onChange(newValue)
  }

  render () {
    const { childParameters, isReadOnly, name } = this.props

    // Map twice: once for each repeated set of childParameters, and once for each parameter within each set
    return (
      <div className='param-list'>
        <h2>This is my list of parameters</h2>
        <ul>
          {this.value.map((item, index) => (
            <li>
              <ChildForm
                childParameters={childParameters}
                value={item}
                commonProps={this.props}
                onChange={this.onChangeChildFormValue}
                index={index}
              />
            </li>
          ))}
        </ul>
        {isReadOnly ? null : (
          <button
            type='button'
            className='add'
            name={`${name}[add]`}
            onClick={this.onAdd}
          >
            <i className='icon-add' /> Add
          </button>
        )}
      </div>
    )
  }
}