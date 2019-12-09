import React from 'react'
import PropTypes from 'prop-types'
import Param from './Param'
import { MaybeLabel, paramFieldToParamProps } from './util'
import { Trans } from '@lingui/macro'

// A single repetition of the set of parameters defined by param_fields.child_parameters
// which is ultimately set by the 'child_parameters' key of the 'list' parameter type in the module YAML
class ChildParamsForm extends React.PureComponent {
  static propTypes = {
    childParameters: PropTypes.array.isRequired, // essentially a copy of the child_parameters key in the module YAML
    value: PropTypes.object.isRequired,
    upstreamValue: PropTypes.object.isRequired, // idName: upstreamValue for all child params
    commonProps: PropTypes.object.isRequired,
    index: PropTypes.number.isRequired, // passed in rather than parent needing to create a closure, which causes re-render
    onChange: PropTypes.func.isRequired, // func(index, value of all form fields) => undefined
    onDelete: PropTypes.func // func(index) => undefined, or null if isReadOnly
  }

  handleChangeParam = (idName, childParamValue) => {
    const { value, index, onChange } = this.props
    onChange(index, {
      ...value,
      [idName]: childParamValue
    })
  }

  handleClickDelete = (ev) => {
    this.props.onDelete(this.props.index)
  }

  render () {
    const { childParameters, value, upstreamValue, commonProps, onDelete, name, fieldId } = this.props
    return (
      <>
        {childParameters.map(childParameter => (
          <Param
            key={childParameter.idName}
            {...commonProps}
            {...paramFieldToParamProps(childParameter)}
            name={childParameter.idName /* should be `${name}[${childParameter.idName}]` but that breaks event handlers */}
            fieldId={`${fieldId}_${childParameter.idName}`}
            value={value[childParameter.idName]}
            upstreamValue={upstreamValue[childParameter.idName]}
            onChange={this.handleChangeParam}
          />
        ))}
        {onDelete ? (
          <div className='delete'>
            <button
              type='button'
              className='delete'
              name={`${name}[delete]`}
              onClick={this.handleClickDelete}
            >
              <i className='icon-close' />
            </button>
          </div>
        ) : null}
      </>
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
    // there are going to be many other props here, which we pass into <ChildForm> as commonProps
    // see <Param> creation in ParamsForm for a list of these props
  }

  /**
   * List of child parameter values, for all repetitions, or default (one repetition) if empty
   */
  get value () {
    const actual = this.props.value
    if (actual.length === 0) {
      return [this.props.childDefault]
    } else {
      return actual
    }
  }

  handleChangeChildFormValue = (index, childFormValue) => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue[index] = childFormValue // may append an element
    onChange(newValue)
  }

  handleDeleteChildForm = (index) => {
    const { onChange, isReadOnly } = this.props
    if (isReadOnly) return
    const newValue = this.value.slice()
    newValue.splice(index, 1)
    onChange(newValue)
  }

  handleAdd = () => {
    const { onChange, isReadOnly, childDefault } = this.props
    if (isReadOnly) return
    const newValue = [...this.value, childDefault]
    onChange(newValue)
  }

  render () {
    const { childParameters, isReadOnly, name, label, fieldId, upstreamValue, childDefault } = this.props

    // Map twice: once for each repeated set of childParameters, and once for each parameter within each set
    return (
      <>
        <MaybeLabel fieldId={`${fieldId}_0_${childParameters[0].idName}`} label={label} />
        <ul>
          {this.value.map((item, index) => (
            <li key={index}>
              <ChildParamsForm
                childParameters={childParameters}
                value={item}
                name={`${name}[${index}]`}
                fieldId={`${fieldId}_${index}`}
                commonProps={this.props}
                upstreamValue={upstreamValue[index] || childDefault}
                onChange={this.handleChangeChildFormValue}
                onDelete={isReadOnly ? null : this.handleDeleteChildForm}
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
            onClick={this.handleAdd}
          >
            <i className='icon-add' />
            <Trans id='js.params.List.add'>Add</Trans>
          </button>
        )}
      </>
    )
  }
}
