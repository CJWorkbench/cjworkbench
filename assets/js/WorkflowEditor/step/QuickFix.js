import React from 'react'
import PropTypes from 'prop-types'

export const QuickFixPropTypes = {
  buttonText: PropTypes.string.isRequired,
  action: PropTypes.oneOfType([
    PropTypes.exact({
      type: PropTypes.oneOf(['prependStep']).isRequired,
      moduleSlug: PropTypes.string.isRequired,
      partialParams: PropTypes.object.isRequired
    }).isRequired
  ]).isRequired
}

export default class QuickFix extends React.PureComponent {
  static propTypes = {
    ...QuickFixPropTypes,
    disabled: PropTypes.bool.isRequired,
    applyQuickFix: PropTypes.func.isRequired // func(action, args) => undefined
  }

  handleClick = () => {
    const { action, applyQuickFix } = this.props
    applyQuickFix(action)
  }

  render () {
    const { disabled, buttonText } = this.props

    return (
      <button
        disabled={disabled}
        className='quick-fix action-button button-orange'
        onClick={this.handleClick}
      >
        {buttonText}
      </button>
    )
  }
}
