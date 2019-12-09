import React, { useEffect } from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import Select from 'react-select'
import { Popper } from 'react-popper'
import { withI18n } from '@lingui/react'
import { t } from '@lingui/macro'

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
    order: 1,
    fn: (data) => {
      // Modify in-place, for speed (we're called often)
      data.styles.width = data.offsets.reference.width
      return data
    }
  },
  preventOverflow: {
    boundariesElement: 'viewport'
  }
}
const PopperMenuPortalContents = React.forwardRef(({ style, placement, scheduleUpdate, children }, ref) => {
  // When menu entries change, update Popper. That handles this case:
  //
  // 1. Open menu from near bottom of page. It opens upward.
  // 2. Search. Number of menu entries shrinks.
  //
  // Expected results: menu is repositioned so its _bottom_ stays in a constant
  // position. That requires a scheduleUpdate().
  useEffect(scheduleUpdate)

  return (
    <div
      ref={ref}
      className='react-select-menu-portal'
      style={style}
      data-placement={placement}
      children={children}
    />
  )
})
function PopperMenuPortal (props) {
  return ReactDOM.createPortal((
    <Popper
      referenceElement={props.controlElement}
      placement={props.menuPlacement}
      modifiers={PopperModifiers}
    >
      {({ ref, style, placement, scheduleUpdate }) => (
        <PopperMenuPortalContents
          ref={ref}
          style={style}
          placement={placement}
          scheduleUpdate={scheduleUpdate}
          children={props.children}
        />
      )}
    </Popper>
  ), props.appendTo)
}

const DefaultOverrideComponents = {
  MenuPortal: PopperMenuPortal
}

class ReactSelect extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // <input name="...">
    inputId: PropTypes.string.isRequired, // <input id="...">
    placeholder: PropTypes.string.isRequired,
    options: PropTypes.arrayOf(PropTypes.shape({
      label: PropTypes.string.isRequired,
      value: PropTypes.any.isRequired
    }).isRequired).isRequired,
    value: PropTypes.oneOfType([
      // either selected === options[X].value or selected[a] === options[X].value
      PropTypes.arrayOf(PropTypes.any.isRequired).isRequired,
      PropTypes.any.isRequired
    ]), // or null|undefined
    isLoading: PropTypes.bool, // default null
    isMulti: PropTypes.bool, // default false
    addMenuListClassName: PropTypes.string, // default undefined. Queried by MenuList in Multicolumn.js
    noOptionsMessage: PropTypes.string, // default 'No options'
    components: PropTypes.object, // or undefined -- overrides react-select components
    onChange: PropTypes.func.isRequired, // func(value|null or [values]) => undefined
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    })
  }

  components = {
    ...DefaultOverrideComponents,
    ...(this.props.components || {})
  }

  noOptionsMessage = () => this.props.noOptionsMessage || this.props.i18n._(t('js.params.common.ReactSelect.noOptionsMessage')`No options`)

  handleChange = (reactSelectValue) => {
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
    const { name, inputId, placeholder, options, isLoading, isMulti, isReadOnly, addMenuListClassName, value } = this.props

    let reactSelectValue
    if (isMulti) {
      reactSelectValue = options ? options.filter(option => value.includes(option.value)) : []
    } else {
      reactSelectValue = options ? (options.find(option => value === option.value) || null) : null
    }

    const classNames = ['react-select']
    classNames.push(isMulti ? 'multiple' : 'single')
    if (isLoading) classNames.push('loading')

    // addMenuListClassName prop will be read by <MenuList> in Multicolumn

    return (
      <Select
        name={name}
        inputId={inputId}
        options={options}
        value={reactSelectValue}
        isLoading={isLoading}
        isMulti={isMulti || false}
        className={classNames.join(' ')}
        classNamePrefix='react-select'
        addMenuListClassName={addMenuListClassName}
        menuPortalTarget={document.body /* passed as props.appendTo to PopperMenuPortal */}
        styles={NoStyles}
        components={this.components}
        noOptionsMessage={this.noOptionsMessage}
        onChange={this.handleChange}
        isClearable={false}
        isDisabled={isReadOnly}
        placeholder={placeholder}
      />
    )
  }
}

export default withI18n()(ReactSelect)
