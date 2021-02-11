import { PureComponent } from 'react'
import PropTypes from 'prop-types'

export default class Checkbox extends PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    value: PropTypes.bool, // or `null` if server has not given a value
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  handleChange = (ev) => {
    const { onChange } = this.props
    onChange(ev.target.checked)
  }

  render () {
    const { name, fieldId, label, isReadOnly, value } = this.props
    return (
      <>
        <div className='checkbox-container'>
          <input
            type='checkbox'
            readOnly={isReadOnly}
            checked={value || false}
            name={name}
            id={fieldId}
            onChange={this.handleChange}
          />
          <label htmlFor={fieldId}>
            {' '}{label}
          </label>
        </div>
      </>
    )
  }
}
