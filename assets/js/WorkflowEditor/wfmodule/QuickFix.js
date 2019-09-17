import React from 'react'
import PropTypes from 'prop-types'
import I18nMessage from '../I18nMessage'

export const QuickFixPropTypes = {
  buttonText: PropTypes.shape({
    id: PropTypes.string.isRequired, // message ID
    arguments: PropTypes.object.isRequired // arguments
  }).isRequired,
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
        <I18nMessage {...buttonText} />
      </button>
    )
  }
}
