// ---- StatusLine ----

// Display error message, if any
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
import React from 'react'
import PropTypes from 'prop-types'

const QuickFixPropTypes = {
    text: PropTypes.string.isRequired,
    action: PropTypes.oneOf(['prependModule']).isRequired,
    args: PropTypes.array.isRequired
}

class QuickFix extends React.PureComponent {
  static propTypes = {
    ...QuickFixPropTypes,
    disabled: PropTypes.bool.isRequired,
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
  }

  onClick = () => {
    const { action, args, applyQuickFix } = this.props
    applyQuickFix(action, args)
  }

  render () {
    const { disabled, text } = this.props

    return (
      <button
        disabled={disabled}
        className="quick-fix action-button button-orange"
        onClick={this.onClick}
      >
        {text}
      </button>
    )
  }
}

export default class StatusLine extends React.PureComponent {
  static propTypes = {
    status: PropTypes.oneOf(['ok', 'waiting', 'busy', 'error', 'unreachable']).isRequired,
    error: PropTypes.string, // may be empty string
    quickFixes: PropTypes.arrayOf(PropTypes.shape(QuickFixPropTypes).isRequired).isRequired,
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
  }

  state = {
    clickedAnyQuickFix: false
  }

  componentDidUpdate (prevProps) {
    // Reset clickedAnyQuickFix, so newly-rendered quick-fix buttons will be
    // clickable.
    //
    // The "correct" approach here would probably be for the parent to supply
    // a `key=...` attribute. But at the moment, this hack takes less code.
    const props = this.props
    if (props.status !== prevProps.status || props.error !== prevProps.error || props.quickFixes !== prevProps.quickFixes) {
      // Whenever the error state changes, let users click things again.
      this.setState({ clickedAnyQuickFix: false })
    }
  }

  applyQuickFix = (...args) => {
    this.setState({ clickedAnyQuickFix: true })
    this.props.applyQuickFix(...args)
  }

  render () {
    const { status, error, quickFixes } = this.props
    const { clickedAnyQuickFix } = this.state

    if (!error && !quickFixes.length) return null

    let quickFixUl = null
    if (quickFixes.length) {
      quickFixUl = (
        <ul className="quick-fixes">
          {quickFixes.map(qf => (
            <li key={qf.text}>
              <QuickFix
                {...qf}
                disabled={clickedAnyQuickFix}
                applyQuickFix={this.applyQuickFix}
              />
            </li>
          ))}
        </ul>
      )
    }

    return (
      <div className="wf-module-error-msg">
        <p>{error}</p>
        {quickFixUl}
      </div>
    )
  }
}
