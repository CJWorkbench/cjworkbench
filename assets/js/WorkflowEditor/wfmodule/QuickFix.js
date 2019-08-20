import React from 'react'
import PropTypes from 'prop-types'

export const QuickFixPropTypes = {
  text: PropTypes.string.isRequired,
  action: PropTypes.oneOf(['prependModule']).isRequired,
  args: PropTypes.array.isRequired
}

export default class QuickFix extends React.PureComponent {
  static propTypes = {
    ...QuickFixPropTypes,
    disabled: PropTypes.bool.isRequired,
    applyQuickFix: PropTypes.func.isRequired // func(action, args) => undefined
  }

  handleClick = () => {
    const { action, args, applyQuickFix } = this.props
    applyQuickFix(action, args)
  }

  render () {
    const { disabled, text } = this.props

    return (
      <button
        disabled={disabled}
        className='quick-fix action-button button-orange'
        onClick={this.handleClick}
      >
        {text}
      </button>
    )
  }
}
