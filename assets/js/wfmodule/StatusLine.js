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


class QuickFix extends React.Component {
  static propTypes = {
    ...QuickFixPropTypes,
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
  }

  onClick = () => {
    const { action, args, applyQuickFix } = this.props
    applyQuickFix(action, args)
  }

  render () {
    const { text } = this.props

    return (
      <button className="quick-fix" onClick={this.onClick}>{text}</button>
    )
  }
}

export default class StatusLine extends React.Component {
  static propTypes = {
    status: PropTypes.oneOf(['busy', 'ready', 'error']).isRequired,
    error: PropTypes.string, // may be empty string
    quickFixes: PropTypes.arrayOf(PropTypes.shape(QuickFixPropTypes).isRequired).isRequired,
    applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
  }

  render () {
    const { status, error, applyQuickFix, quickFixes } = this.props

    if (!error && !quickFixes.length) return null

    let quickFixUl = null
    if (quickFixes.length) {
      quickFixUl = (
        <ul className="quick-fixes">
          {quickFixes.map(qf => <li key={qf.text}><QuickFix {...qf} applyQuickFix={applyQuickFix} /></li>)}
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
