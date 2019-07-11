import React from 'react'
import PropTypes from 'prop-types'
import { OperatorPropType } from './PropTypes'

class OneOperator extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    operator: OperatorPropType.isRequired,
    checked: PropTypes.bool.isRequired,
    onClick: PropTypes.func.isRequired
  }

  onClick = () => {
    const { onClick, operator } = this.props
    onClick(operator)
  }

  render () {
    const { name, operator, checked } = this.props
    const text = operator === 'and' ? 'AND' : 'OR'

    return checked ? (
      <span className='selected-operator'>{text}</span>
    ) : (
      <button
        type='button'
        className='unselected-operator'
        onClick={this.onClick}
      >{text}</button>
    )
  }
}

export default class FilterOperator extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    value: OperatorPropType.isRequired,
    onChange: PropTypes.func.isRequired // onChange('add' or 'or') => undefined
  }

  render () {
    const { isReadOnly, name, value, onChange } = this.props

    return (
      <div className='filter-operator'>
        {(!isReadOnly || value === 'and') ? (
          <OneOperator
            name={`${name}[and]`}
            operator='and'
            checked={value === 'and'}
            onClick={onChange}
          />
        ) : null}
        {(!isReadOnly || value == 'or') ? (
          <OneOperator
            name={`${name}[or]`}
            operator='or'
            checked={value === 'or'}
            onClick={onChange}
          />
        ) : null}
      </div>
    )
  }
}
