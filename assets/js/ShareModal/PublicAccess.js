import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import ShareableLink from './ShareableLink'

function ShareableLinks (props) {
  const { url, isPublic } = props

  return (
    <ul className='shareable-links'>
      <ShareableLink
        component='li'
        title={t({ id: 'js.ShareModal.ShareableLinks.workflow.title', message: 'Workflow link' })}
        url={url}
        showShareHeader
        isPublic={isPublic}
      />
      <ShareableLink
        component='li'
        title={t({ id: 'js.ShareModal.ShareableLinks.report.title', message: 'Report link' })}
        url={`${url}/report`}
        showShareHeader={false}
        isPublic={isPublic}
      />
    </ul>
  )
}
ShareableLinks.propTypes = {
  url: PropTypes.string.isRequired, // e.g., `/workflows/1`
  isPublic: PropTypes.bool.isRequired,
}

export default function PublicAccess (props) {
  const {
    workflowId,
    isPublic,
    secretId,
    canCreateSecretLink,
    setWorkflowPublicAccess,
    isReadOnly
  } = props
  // submitState:
  //
  // * isPublic: we're going to set things public
  // * hasSecret: we want a secret link to exist
  // * submitting: we are actually submitting (as opposed to just prompting
  //   the user for confirmation).
  // { isPublic, hasSecret, submitting } bools
  const [submitState, setSubmitState] = React.useState(null)

  const [showIsPublic, showHasSecret] = (submitState && submitState.submitting)
    ? [submitState.isPublic, submitState.hasSecret]
    : [isPublic, Boolean(secretId)]
  const selectedMenuOption = showIsPublic
    ? 'public'
    : (showHasSecret ? 'secret' : 'private')

  const submit = React.useCallback(({ isPublic, hasSecret }) => {
    setSubmitState({ isPublic, hasSecret, submitting: true })
    setWorkflowPublicAccess(isPublic, hasSecret)
      .then(() => setSubmitState(null))
  }, [setSubmitState, setWorkflowPublicAccess])

  const handleChange = React.useCallback(ev => {
    const nextMenuOption = ev.target.value

    if (nextMenuOption === 'private') {
      if (secretId) {
        setSubmitState({ isPublic: false, hasSecret: false, submitting: false })
      } else {
        submit({ isPublic: false, hasSecret: false })
      }
    } else if (nextMenuOption === 'secret') {
      submit({ isPublic: false, hasSecret: true })
    } else {
      submit({ isPublic: true, hasSecret: Boolean(secretId) })
    }
  }, [isPublic, secretId, submitState, setSubmitState, submit])

  const handleClickDeleteSecretId = React.useCallback(() => {
    submit({ isPublic: false, hasSecret: false })
  }, [submit])

  const handleClickCancelSubmitting = React.useCallback(() => {
    setSubmitState(null)
  }, [setSubmitState])

  const promptingToDeleteSecretId = Boolean(submitState && Boolean(secretId) && !submitState.hasSecret)

  return (
    <>
      <fieldset className='share-public-options' disabled={submitState ? submitState.submitting : false}>
        <legend>
          <Trans id='js.ShareModal.PublicAccess.title'>Public Access</Trans>
        </legend>
        <div className={`share-level-option${promptingToDeleteSecretId ? ' prompting' : ''}`}>
          <label className='share-level-private'>
            <input
              type='radio'
              name='share-level'
              value='private'
              readOnly={isReadOnly}
              checked={selectedMenuOption === 'private'}
              onChange={handleChange}
              disabled={isReadOnly || promptingToDeleteSecretId}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.private.title'>Private</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.private.description'>Only collaborators can see this workflow</Trans></small>
          </label>
          {promptingToDeleteSecretId
            ? (
              <p className='prompt confirm-delete-secret-links'>
                <Trans id='js.ShareModal.PublicAccess.confirmDeleteSecretLink.prompt'>
                  <strong>Delete secret link?</strong> <small>It will be gone forever.</small>
                </Trans>
                <button
                  type='button'
                  name='delete-secret-link'
                  onClick={handleClickDeleteSecretId}
                  disabled={submitState.submitting}
                >
                  <Trans id='js.ShareModal.publicAccess.confirmDeleteSecretLink.confirm'>
                    Delete
                  </Trans>
                </button>
                <button
                  type='button'
                  name='cancel'
                  onClick={handleClickCancelSubmitting}
                  disabled={submitState.submitting}
                >
                  <Trans id='js.ShareModal.publicAccess.confirmDeleteSecretLink.cancel'>
                    Cancel
                  </Trans>
                </button>
              </p>
              )
            : null}
        </div>
        <div className='share-level-option'>
          <label className='share-level-secret'>
            <input
              type='radio'
              name='share-level'
              value='secret'
              readOnly={isReadOnly}
              disabled={isReadOnly || (!secretId && !canCreateSecretLink) || promptingToDeleteSecretId}
              checked={selectedMenuOption === 'secret'}
              onChange={handleChange}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.secret.title'>Secret link</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.secret.description'>Anyone with the link can see this workflow and its collaborators</Trans></small>
          </label>
          {!isReadOnly && !secretId && !canCreateSecretLink
            ? (
              <p className='prompt'>
                <a href='/settings/plan' target='_blank' rel='noopener noreferrer'>
                  <Trans
                    id='js.ShareModal.PublicAccess.secret.upgrade'
                    comment='A prompt to upgrade; clicking the link goes to the Plans page'
                  >
                    Upgrade
                  </Trans>
                </a>
              </p>
              )
            : null}
        </div>
        <div className='share-level-option'>
          <label className='share-level-public'>
            <input
              type='radio'
              name='share-level'
              value='public'
              readOnly={isReadOnly}
              disabled={isReadOnly || promptingToDeleteSecretId}
              checked={selectedMenuOption === 'public'}
              onChange={handleChange}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.public.title'>Public</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.public.description'>Anyone on the Internet can see this workflow and its collaborators</Trans></small>
          </label>
        </div>
      </fieldset>

      {isPublic
        ? <ShareableLinks url={`${window.origin}/workflows/${workflowId}`} isPublic />
        : null}
      {!isPublic && secretId
        ? <ShareableLinks url={`${window.origin}/workflows/${secretId}`} isPublic={false} />
        : null}
    </>
  )
}
PublicAccess.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isReadOnly: PropTypes.bool.isRequired, // can the viewer edit permissions?
  isPublic: PropTypes.bool.isRequired,
  secretId: PropTypes.string.isRequired, // "" for no-secret
  canCreateSecretLink: PropTypes.bool.isRequired,
  setWorkflowPublicAccess: PropTypes.func.isRequired // func(isPublic, hasSecret) => Promise[undefined]
}
