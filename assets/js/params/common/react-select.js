import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import Select from 'react-select'
import { Manager, Target, Popper } from 'react-popper'


// react-select includes a funky CSS engine we don't want. Disable
// _all_ its styles using its 'styles' parameter.
//
// This disables the _positioning_ of the menu, too. We'll use Popper
// to position the menu -- react-select's positioning is broken. That's
// https://www.pivotaltracker.com/story/show/163066332
const NoStyle = {}
export const NoStyles = {
  clearIndicator: () => NoStyle,
  container: () => NoStyle,
  control: () => NoStyle,
  dropdownIndicator: () => NoStyle,
  group: () => NoStyle,
  groupHeading: () => NoStyle,
  indicatorsContainer: () => NoStyle,
  indicatorSeparator: () => NoStyle,
  input: () => NoStyle,
  loadingIndicator: () => NoStyle,
  loadingMessage: () => NoStyle,
  menu: () => NoStyle,
  menuList: () => NoStyle,
  menuPortal: () => NoStyle,
  multiValue: () => NoStyle,
  multiValueLabel: () => NoStyle,
  multiValueRemove: () => NoStyle,
  noOptionsMessage: () => NoStyle,
  option: () => NoStyle,
  placeholder: () => NoStyle,
  singleValue: () => NoStyle,
  valueContainer: () => NoStyle
}


const PopperModifiers = {
  autoPopperWidth: {
    enabled: true,
    order: 840,
    fn: (data) => {
      // Modify in-place, for speed (we're called often)
      data.styles.width = data.offsets.reference.width
      return data
    }
  }
}
function PopperMenuPortal (props) {
  return ReactDOM.createPortal((
    <Popper
      positionFixed
      placement={props.placement}
      target={props.controlElement}
      modifiers={PopperModifiers}
    >
      {({ popperProps, restProps, scheduleUpdate }) => (
        <div
          {...popperProps}
          children={props.children}
        />
      )}
    </Popper>
  ), props.appendTo)
}


const DefaultOverrideComponents = {
  MenuPortal: PopperMenuPortal,
}


export default class ReactSelect extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name="...">
    inputId: PropTypes.string.isRequired, // <input id="...">
    placeholder: PropTypes.string.isRequired,
    options: PropTypes.arrayOf(PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.any.isRequired,
    }).isRequired).isRequired,
    value: PropTypes.oneOfType([
      // either selected === options[X].value or selected[a] === options[X].value
      PropTypes.arrayOf(PropTypes.any.isRequired).isRequired,
      PropTypes.any.isRequired,
    ]), // or null|undefined
    isLoading: PropTypes.bool, // default null
    isMulti: PropTypes.bool, // default false
    components: PropTypes.object, // or undefined -- overrides react-select components
    onChange: PropTypes.func.isRequired // func(value|null or [values]) => undefined
  }

  components = {
    ...DefaultOverrideComponents,
    ...(this.props.components || {})
  }

  onChange = (reactSelectValue) => {
    const { isMulti, onChange } = this.props

    let value
    if (isMulti) {
      value = reactSelectValue.map(({ value }) => value)
    } else {
      value = reactSelectValue ? reactSelectValue.value : null
    }

    onChange(value)
  }

  render () {
    const { name, inputId, placeholder, options, selected, isLoading, isMulti, isReadOnly, value } = this.props

    let reactSelectValue
    if (isMulti) {
      reactSelectValue = options ? options.filter(option => value.includes(option.value)) : []
    } else {
      reactSelectValue = options ? (options.find(option => value === option.value) || null) : null
    }

    const className = `react-select ${isMulti ? 'multiple' : 'single'}${isLoading ? ' loading' : ''}`

    return (
      <Select
        name={name}
        inputId={inputId}
        options={options}
        value={reactSelectValue}
        isLoading={isLoading}
        isMulti={isMulti || false}
        className={className}
        classNamePrefix='react-select'
        menuPortalTarget={document.body /* passed as props.appendTo to PopperMenuPortal */}
        styles={NoStyles}
        components={this.components}
        onChange={this.onChange}
        isClearable={false}
        isDisabled={isReadOnly}
        placeholder={placeholder}
      />
    )
  }
}
