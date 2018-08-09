import React from 'react'
import PropTypes from 'prop-types'

/**
 * A text field for single-line text that ... wraps! Yay!
 *
 * It grows to the It also has a submit button that appears when the value has changed.
 *
 * This field maintains no state. Its parent component must maintain its
 * `initialValue` (the value before edits) and `value` (the value it sends in
 * `onChange(value)`). It will call `onSubmit()` when the user presses Enter
 * or clicks its submit button; at that point the parent should do something
 * with the last-given `onChange(value)`.
 */
export default class SingleLineTextField extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(str) => undefined
    onSubmit: PropTypes.func.isRequired, // func() => undefined
    onReset: PropTypes.func.isRequired, // func() => undefined
    name: PropTypes.string.isRequired,
    initialValue: PropTypes.string, // sometimes empty string
    value: PropTypes.string, // sometimes empty string
    placeholder: PropTypes.string // sometimes empty string
  }

  buttonRef = React.createRef()
  calculatorRef = React.createRef()

  state = {
    rows: 1
  }

  onChange = (ev) => {
    // Remove newlines. We simply won't let this input produce one.
    const value = ev.target.value.replace(/[\r\n]/g, '')
    this.props.onChange(value)
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 13: // Enter
        ev.preventDefault()
        return this.props.onSubmit()
      case 27: // Escape
        ev.preventDefault()
        return this.props.onReset()
      // else handle the key as usual
    }
  }

  componentDidMount () {
    this._refreshRows()
  }

  componentDidUpdate (prevProps) {
    if (prevProps.value !== this.props.value || prevProps.initialValue !== this.props.initialValue) {
      this._refreshRows()
    }
  }

  _refreshRows () {
    // The hidden <span> contains the same text (and if the CSS is correct,
    // styles) as the <textarea>. We'll use getClientRects() to determine the
    // number of rows the <textarea> needs to contain all the text
    const span = this.calculatorRef.current
    const button = this.buttonRef.current

    const rects = span.getClientRects()
    const nTextRows = rects.length

    if (rects.length === 0) {
      // unit tests
      this.setState({ rows: 1 })
      return
    }

    // If there's a submit button and the text would overlap it, add another
    // row so the submit button can go there
    const lastRectRight = rects[rects.length - 1].right
    const buttonLeft = button ? button.getBoundingClientRect().left : null
    const lastRectOverlaps = button ? lastRectRight > buttonLeft : false

    const rows = nTextRows + (lastRectOverlaps ? 1 : 0)

    this.setState({ rows })
  }

  render () {
    const { name, initialValue, value, placeholder, isReadOnly } = this.props
    const { rows } = this.state
    const maybeButton = initialValue === value ? null : (
      <button title="submit" ref={this.buttonRef} onClick={this.props.onSubmit}>
        <i className="icon-play" />
      </button>
    )

    // https://developer.mozilla.org/en-US/docs/Web/API/Element/getClientRects
    // ... a <span>'s .getClientRects() will return a rect per line. (That isn't
    // true of a <div>.)
    return (
      <div className="single-line-text-field">
        <div className="resize-calculator">
          <span ref={this.calculatorRef}>{value}</span>
        </div>
        <textarea
          readOnly={isReadOnly}
          name={name}
          placeholder={placeholder}
          rows={rows}
          onChange={this.onChange}
          onKeyDown={this.onKeyDown}
          value={value}
        />
        {maybeButton}
      </div>
    )
  }
}
