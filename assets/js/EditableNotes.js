import React from 'react'
import TextareaAutosize from 'react-textarea-autosize'
import PropTypes from 'prop-types'

export default class EditableNotes extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    placeholder: PropTypes.string.isRequired,
    value: PropTypes.string,
    inputRef: PropTypes.object,
    onChange: PropTypes.func,
    onBlur: PropTypes.func,
    onCancel: PropTypes.func.isRequired
  }

  // Make Enter key blur by default, instead of adding newline.
  handleKeyDown = (ev) => {
    if (ev.target.tagName === 'TEXTAREA' && ev.key === 'Enter') {
      ev.preventDefault()
      ev.target.blur() // triggers this.props.onBlur, if set
    }

    if (ev.target.tagName === 'TEXTAREA' && ev.key === 'Escape') {
      this.props.onCancel()
      ev.target.blur() // triggers this.props.onBlur, if set
    }
  }

  hackAroundTextareaAutosizeObsoleteInputRef = (ref) => {
    if (this.props.inputRef) {
      this.props.inputRef.current = ref
    }
  }

  componentWillUnmount () {
    // see hackAroundTextareaAutosizeObsoleteInputRef()
    if (this.props.inputRef) {
      this.props.inputRef.current = null
    }
  }

  render () {
    // We pass most props to the <TextareaAutosize>.
    const subprops = Object.assign({}, this.props)
    delete subprops.isReadOnly
    delete subprops.onKeyDown
    subprops.inputRef = this.hackAroundTextareaAutosizeObsoleteInputRef

    // Saves a ref to parent to allow targeting of imported component
    if (this.props.isReadOnly) {
      return (
        <div className='editable-notes-read-only'>
          {this.props.value}
        </div>
      )
    } else {
      return (
        <TextareaAutosize
          name='notes'
          {...subprops}
          onKeyDown={this.handleKeyDown}
        />
      )
    }
  }
}
