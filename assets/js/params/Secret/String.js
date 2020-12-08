import React from 'react'
import PropTypes from 'prop-types'
import { MaybeLabel } from '../util'
import { timeDifference } from '../../utils'
import { i18n } from '@lingui/core'
import { Trans } from '@lingui/macro'

/**
 * Prompt the user to enter a string: show a <label>, <input>, <button> and <p className='help'>.
 *
 * When the user clicks "submit", the state of this container will change irreversibly.
 */
function StringPrompt ({ label, name, fieldId, placeholder, pattern, help, helpUrl, helpUrlPrompt, submit }) {
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
          disabled={isSubmitted}
        />
        <button
          type='button'
          className='set-secret'
          onClick={handleSubmit}
          disabled={isSubmitted || !isValid}
        >
          Save
        </button>
      </div>
      <p className='help'>
        <span className='text'>{help}</span>
        <a target='_blank' rel='noopener noreferrer' href={helpUrl}>{helpUrlPrompt}</a>
      </p>
    </>
  )
}

function StringDisplay ({ isOwner, secretMetadata, label, name, fieldId, deleteSecret }) {
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
        {isOwner ? (
          <button
            type='button'
            className='clear-secret'
            onClick={handleSubmit}
            disabled={isSubmitted}
          >
            <Trans id='js.params.Secret.String.StringDisplay.clear.button'>Clear</Trans>
          </button>
        ) : null}
      </div>
    </>
  )
}

export default function String_ ({ secretMetadata, isOwner, name, fieldId, secretLogic: { label, placeholder, pattern, help, helpUrl, helpUrlPrompt }, submitSecret, deleteSecret }) {
  if (secretMetadata) {
    return (
      <StringDisplay
        isOwner={isOwner}
        secretMetadata={secretMetadata}
        label={label}
        name={name}
        fieldId={fieldId}
        deleteSecret={deleteSecret}
      />
    )
  } else if (isOwner) {
    return (
      <StringPrompt
        isOwner={isOwner}
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
  } else {
    return (
      <p className='not-owner'>
        <Trans id='js.params.Secret.String.onlyOwnerCanEnterSecret'>Not authenticated. Only the workflow owner may authenticate.</Trans>
      </p>
    )
  }
}
String_.propTypes = {
  isOwner: PropTypes.bool.isRequired,
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
