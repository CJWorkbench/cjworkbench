import { useCallback } from 'react'
import PropTypes from 'prop-types'

function TextareaAutosize (props, ref) {
  const { name, value, inputRef, placeholder, onChange, onBlur, onKeyDown } = props

  return (
    <div className='editable-notes'>
      <textarea
        ref={inputRef}
        name={name}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
        onBlur={onBlur}
        onKeyDown={onKeyDown}
      />
      <div className='invisible-size-setter'>{value}</div>
    </div>
  )
}
TextareaAutosize.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  placeholder: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onBlur: PropTypes.func.isRequired,
  onKeyDown: PropTypes.func.isRequired
}

export default function EditableNotes (props) {
  const { inputRef, isReadOnly, placeholder, value, onChange, onBlur, onCancel } = props

  // Make Enter key blur by default, instead of adding newline.
  const handleKeyDown = useCallback(ev => {
    if (ev.target.tagName === 'TEXTAREA' && ev.key === 'Enter') {
      ev.preventDefault()
      ev.target.blur() // triggers this.props.onBlur, if set
    }

    if (ev.target.tagName === 'TEXTAREA' && ev.key === 'Escape') {
      onCancel()
      ev.target.blur() // triggers this.props.onBlur, if set
    }
  }, [onCancel])

  // Saves a ref to parent to allow targeting of imported component
  if (isReadOnly) {
    return (
      <div className='editable-notes-read-only'>{value}</div>
    )
  } else {
    return (
      <TextareaAutosize
        name='notes'
        {...{ placeholder, value, inputRef, onChange, onBlur }}
        onKeyDown={handleKeyDown}
      />
    )
  }
}
EditableNotes.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  placeholder: PropTypes.string.isRequired,
  value: PropTypes.string,
  inputRef: PropTypes.object,
  onChange: PropTypes.func,
  onBlur: PropTypes.func,
  onCancel: PropTypes.func.isRequired
}
