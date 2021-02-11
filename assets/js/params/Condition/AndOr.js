import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import { AndOrPropType } from './PropTypes'
import { Trans } from '@lingui/macro'

class AndOr extends PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    operator: AndOrPropType.isRequired,
    checked: PropTypes.bool.isRequired,
    onClick: PropTypes.func.isRequired
  }

  handleClick = () => {
    const { onClick, operator } = this.props
    onClick(operator)
  }

  render () {
    const { name, operator, checked } = this.props
    const text = operator === 'and'
      ? <Trans id='js.params.Condition.AndOr.and' comment='The logical AND operator'>AND</Trans>
      : <Trans id='js.params.Condition.AndOr.or' comment='The logical OR operator'>OR</Trans>

    return checked
      ? <span className='selected-operator'>{text}</span>
      : (
        <button
          type='button'
          name={name}
          className='unselected-operator'
          onClick={this.handleClick}
        >
          {text}
        </button>
        )
  }
}

export default class Operator extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    value: AndOrPropType.isRequired,
    onChange: PropTypes.func.isRequired // onChange('add' or 'or') => undefined
  }

  render () {
    const { isReadOnly, name, value, onChange } = this.props

    return (
      <div className='andor-operator'>
        {!isReadOnly || value === 'and'
          ? (
            <AndOr
              name={`${name}[and]`}
              operator='and'
              checked={value === 'and'}
              onClick={onChange}
            />
            )
          : null}
        {!isReadOnly || value === 'or'
          ? (
            <AndOr
              name={`${name}[or]`}
              operator='or'
              checked={value === 'or'}
              onClick={onChange}
            />
            )
          : null}
      </div>
    )
  }
}
