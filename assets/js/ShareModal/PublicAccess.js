import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import ShareableLink from './ShareableLink'

function ShareableLinks (props) {
  const { url, isPublic, logShare } = props

  return (
    <div className='shareable-links'>
      <h6>
        <Trans id='js.ShareModal.ShareableLinks.title'>Links for anybody on the Internet</Trans>
      </h6>
      <ul>
        <ShareableLink
          component='li'
          title={t({ id: 'js.ShareModal.ShareableLinks.workflow.title', message: 'Workflow' })}
          url={url}
          isPublic={isPublic}
          logShare={logShare}
        />
        <ShareableLink
          component='li'
          title={t({ id: 'js.ShareModal.ShareableLinks.report.title', message: 'Report' })}
          url={`${url}/report`}
          isPublic={isPublic}
          logShare={logShare}
        />
      </ul>
    </div>
  )
}
ShareableLinks.propTypes = {
  url: PropTypes.string.isRequired, // e.g., `/workflows/1`
  isPublic: PropTypes.bool.isRequired,
  logShare: PropTypes.func.isRequired // func('Facebook'|'Twitter'|'URL copied') => undefined
}

export default function PublicAccess (props) {
  const {
    workflowId,
    isPublic,
    secretId,
    canCreateSecretLink,
    setWorkflowPublicAccess,
    logShare,
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

  const [showIsPublic, showHasSecret] = submitState
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

  return (
    <>
      <fieldset className='share-public-options' disabled={submitState ? submitState.submitting : false}>
        <legend>
          <Trans id='js.ShareModal.PublicAccess.title'>Who can see this workflow</Trans>
        </legend>
        <div className='share-level-option'>
          <label className='share-level-private'>
            <input
              type='radio'
              name='share-level'
              value='private'
              readOnly={isReadOnly}
              checked={selectedMenuOption === 'private'}
              onChange={handleChange}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.private.title'>Private</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.private.description'>Only collaborators can see this workflow</Trans></small>
          </label>
          {submitState && Boolean(secretId) && !submitState.hasSecret
            ? (
              <p className='prompt'>
                <Trans id='js.ShareModal.PublicAccess.confirmDeleteSecretLink.prompt'>
                  <strong>Delete secret link?</strong> Everyone who uses it will lose access.
                </Trans>
                <button
                  type='submit'
                  className='btn btn-orange'
                  onClick={handleClickDeleteSecretId}
                  disabled={submitState.submitting}
                >
                  <Trans id='js.ShareModal.publicAccess.confirmDeleteSecretLink.button'>
                    Delete secret link
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
              disabled={!secretId && !canCreateSecretLink}
              readOnly={isReadOnly}
              checked={selectedMenuOption === 'secret'}
              onChange={handleChange}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.secret.title'>Secret Link</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.secret.description'>Anyone with the link can see this workflow and its collaborators.</Trans></small>
          </label>
          {!secretId && !canCreateSecretLink
            ? (
              <p className='requires-paid-plan'>
                <Trans id='js.ShareModal.PublicAccess.secret.requiresPaidPlan'>Requires paid plan. <a href='/settings/plan' target='_blank' rel='noopener noreferrer'>Upgrade</a></Trans>
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
              checked={selectedMenuOption === 'public'}
              onChange={handleChange}
            />
            <strong><Trans id='js.ShareModal.PublicAccess.public.title'>Public</Trans></strong>
            <small><Trans id='js.ShareModal.PublicAccess.secret.description'>Anyone on the Internet can see this workflow and its collaborators.</Trans></small>
          </label>
        </div>
      </fieldset>

      {isPublic
        ? <ShareableLinks url={`${window.origin}/workflows/${workflowId}`} isPublic logShare={logShare} />
        : null}
      {!isPublic && secretId
        ? <ShareableLinks url={`${window.origin}/workflows/${secretId}`} isPublic={false} logShare={logShare} />
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
  setWorkflowPublicAccess: PropTypes.func.isRequired, // func(isPublic, hasSecret) => Promise[undefined]
  logShare: PropTypes.func.isRequired // func('Facebook'|'Twitter'|'URL copied') => undefined
}
