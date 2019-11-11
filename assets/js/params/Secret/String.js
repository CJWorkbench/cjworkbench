import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from '../util'
import { timeDifference } from '../../utils'
import { withI18n } from '@lingui/react'

/**
 * Prompt the user to enter a string: show a <label>, <input>, <button> and <p className='help'>.
 *
 * When the user clicks "submit", the state of this container will change irreversibly.
 */
function StringPrompt ({ isReadOnly, label, name, fieldId, placeholder, pattern, help, helpUrl, helpUrlPrompt, submit }) {
  const [value, setValue] = React.useState('')
  const [isValid, setValid] = React.useState(false)
  const [isSubmitted, setSubmitted] = React.useState(false)
  const handleChange = React.useCallback(ev => {
    setValue(ev.target.value)
    setValid(ev.target.validity.valid)
  })
  const handleSubmit = React.useCallback(() => {
    if (!isValid) return
    submit(name, value)
    setSubmitted(true)
  })
  const handleKeyDown = React.useCallback(ev => {
    if (ev.key === 'Enter') {
      ev.preventDefault()
      ev.stopPropagation()
      handleSubmit()
    }
  })

  return (
    <>
      <MaybeLabel fieldId={fieldId} label={label} />
      <div className='secret-string-input'>
        <input
          type='text'
          data-name={name}
          id={fieldId}
          value={value}
          pattern={pattern}
          required
          placeholder={placeholder}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          readOnly={isReadOnly}
          disabled={isSubmitted}
        />
        {!isReadOnly ? (
          <button
            type='button'
            className='set-secret'
            onClick={handleSubmit}
            disabled={isSubmitted || !isValid}
          >
            Save
          </button>
        ) : null}
      </div>
      {!isReadOnly ? (
        <p className='help'>
          <span className='text'>{help}</span>
          <a target='_blank' rel='noopener noreferrer' href={helpUrl}>{helpUrlPrompt}</a>
        </p>
      ) : null}
    </>
  )
}

function StringDisplay ({ i18n, isReadOnly, secretMetadata, label, name, fieldId, deleteSecret }) {
  const [isSubmitted, setSubmitted] = React.useState(false)
  const handleSubmit = React.useCallback(() => {
    deleteSecret(name)
    setSubmitted(true)
  })

  const createdAt = secretMetadata.name

  return (
    <>
      <MaybeLabel fieldId={fieldId} label={label} />
      <div className='secret-string-display'>
        <time dateTime={createdAt}>(Secret, saved {timeDifference(Date.parse(createdAt), new Date(), i18n)})</time>
        {!isReadOnly ? (
          <button
            type='button'
            className='clear-secret'
            onClick={handleSubmit}
            disabled={isSubmitted}
          >
            Clear
          </button>
        ) : null}
      </div>
    </>
  )
}

const String_ = React.memo(withI18n()(function String_ ({ i18n, secretMetadata, isReadOnly, name, fieldId, secretLogic: { label, placeholder, pattern, help, helpUrl, helpUrlPrompt }, submitSecret, deleteSecret }) {
  if (secretMetadata) {
    return (
      <StringDisplay
        i18n={i18n}
        isReadOnly={isReadOnly}
        secretMetadata={secretMetadata}
        label={label}
        name={name}
        fieldId={fieldId}
        deleteSecret={deleteSecret}
      />
    )
  } else {
    return (
      <StringPrompt
        isReadOnly={isReadOnly}
        label={label}
        name={name}
        fieldId={fieldId}
        placeholder={placeholder}
        pattern={pattern}
        help={help}
        helpUrl={helpUrl}
        helpUrlPrompt={helpUrlPrompt}
        submit={submitSecret}
      />
    )
  }
}))
String_.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired, // <input name=...>
  fieldId: PropTypes.string.isRequired, // <input id=...>
  secretMetadata: PropTypes.shape({
    name: PropTypes.string.isRequired // ISO8601-formatted date
  }), // or null
  submitSecret: PropTypes.func.isRequired, // func(name, secret) => undefined
  deleteSecret: PropTypes.func.isRequired, // func(name) => undefined
  secretLogic: PropTypes.shape({
    label: PropTypes.string.isRequired,
    placeholder: PropTypes.string.isRequired,
    pattern: PropTypes.string.isRequired,
    help: PropTypes.string.isRequired,
    helpUrl: PropTypes.string.isRequired,
    helpUrlPrompt: PropTypes.string.isRequired
  })
}
export default String_
