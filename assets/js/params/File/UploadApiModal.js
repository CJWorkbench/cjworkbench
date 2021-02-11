import { useState, useEffect, useCallback } from 'react'
import PropTypes from 'prop-types'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter
} from '../../components/Modal'
import { getApiToken, clearApiToken, resetApiToken } from './actions'
import { connect } from 'react-redux'
import { Trans } from '@lingui/macro'

class ApiTokenState {
  constructor (flag, apiToken) {
    this.flag = flag
    this.apiToken = apiToken
  }
}
ApiTokenState.OK = 0
ApiTokenState.LOADING = 1
ApiTokenState.SENDING = 2

function ApiToken ({
  workflowId,
  stepSlug,
  apiTokenState,
  clearApiToken,
  resetApiToken
}) {
  switch (apiTokenState.flag) {
    case ApiTokenState.OK:
      return (
        <ApiTokenOk
          workflowId={workflowId}
          stepSlug={stepSlug}
          apiToken={apiTokenState.apiToken}
          clearApiToken={clearApiToken}
          resetApiToken={resetApiToken}
        />
      )
    case ApiTokenState.LOADING:
      return <ApiTokenLoading />
    case ApiTokenState.SENDING:
      return <ApiTokenSending />
  }
}

function ApiTokenLoading () {
  return (
    <div className='state-loading'>
      <Trans id='js.params.File.UploadApiModal.ApiTokenLoading'>Loading</Trans>
    </div>
  )
}

function ApiTokenSending () {
  return <div className='state-sending'>…</div>
}

function ApiTokenOk ({
  workflowId,
  stepSlug,
  apiToken,
  clearApiToken,
  resetApiToken
}) {
  const createFileUrl = `${window.location.origin}/api/v1/workflows/${workflowId}/steps/${stepSlug}/files`

  return (
    <div className='state-ok'>
      {apiToken
        ? (
          <>
            <p className='actions'>
              <button
                type='button'
                name='clear-api-token'
                className='action-button button-orange--fill'
                onClick={clearApiToken}
              >
                <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.disableApi'>
                  Disable API
                </Trans>
              </button>
            </p>
            <dl>
              <dt>
                <Trans id='js.params.File.UploadApiModal.ApiTokenOk.createFileUrl'>
                  Create-file URL
                </Trans>
              </dt>
              <dd>
                <kbd>{createFileUrl}</kbd>
              </dd>
              <dt>
                <Trans id='js.params.File.UploadApiModal.ApiTokenOk.apiToken'>
                  API Token
                </Trans>
              </dt>
              <dd>
                <kbd>{apiToken}</kbd>
                <button
                  type='button'
                  name='reset-api-token'
                  className='action-button button-blue'
                  onClick={resetApiToken}
                >
                  <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.resetApiToken'>
                    Reset API Token
                  </Trans>
                </button>
              </dd>
            </dl>
          </>
          )
        : (
          <p className='actions'>
            <button
              type='button'
              className='action-button button-orange--fill'
              name='reset-api-token'
              onClick={resetApiToken}
            >
              <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.enableApi'>
                Enable API
              </Trans>
            </button>
          </p>
          )}
    </div>
  )
}

export function UploadApiModal ({
  stepSlug,
  workflowId,
  onClickClose,
  getApiToken,
  resetApiToken,
  clearApiToken
}) {
  const [apiTokenState, setApiTokenState] = useState(
    new ApiTokenState(ApiTokenState.LOADING, null)
  )
  const { apiToken } = apiTokenState
  useEffect(() => {
    getApiToken(stepSlug)
      .then(({ value }) => value)
      .then(apiToken =>
        setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken))
      )
  }, [stepSlug])
  const doResetApiToken = useCallback(() => {
    setApiTokenState(
      new ApiTokenState(ApiTokenState.SENDING, apiTokenState.apiToken)
    )
    resetApiToken(stepSlug)
      .then(({ value }) => value)
      .then(apiToken =>
        setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken))
      )
  })
  const doClearApiToken = useCallback(() => {
    setApiTokenState(new ApiTokenState(ApiTokenState.SENDING, null))
    clearApiToken(stepSlug)
      .then(({ value }) => value)
      .then(apiToken =>
        setApiTokenState(new ApiTokenState(ApiTokenState.OK, null))
      )
  })

  return (
    <Modal className='upload-api-modal' isOpen size='lg' toggle={onClickClose}>
      <ModalHeader>
        <Trans
          id='js.params.Custom.UploadApiModal.header.title'
          comment='This should be all-caps for styling reasons'
        >
          UPLOAD BY API
        </Trans>
      </ModalHeader>
      <ModalBody>
        <h5>
          <Trans id='js.params.Custom.UploadApiModal.programmerInstructions'>
            These instructions are for programmers.
          </Trans>
        </h5>
        <p>
          <Trans id='js.params.Custom.UploadApiModal.theFileUploadApiIsPerfect'>
            You can upload files to Workbench from any cronjob, script or app.
          </Trans>
        </p>
        <p className='status'>
          {apiToken
            ? (
              <Trans
                id='js.params.Custom.UploadApiModal.fileuploadApiStatus.enabled'
                comment='The tag adds emphasis'
              >
                The file-upload API is enabled.
              </Trans>
              )
            : (
              <Trans id='js.params.Custom.UploadApiModal.fileuploadApiStatus.disabled'>
                The file-upload API is disabled. Enable it to upload from a
                program.
              </Trans>
              )}
        </p>
        <ApiToken
          workflowId={workflowId}
          stepSlug={stepSlug}
          apiTokenState={apiTokenState}
          resetApiToken={doResetApiToken}
          clearApiToken={doClearApiToken}
        />
        <p>
          <Trans id='js.params.File.UploadApiModal.ApiTokenOk.instructions'>
            Follow our{' '}
            <a
              href='https://github.com/CJWorkbench/cjworkbench/wiki/File-Upload-API'
              target='_blank'
              rel='noopener noreferrer'
            >
              File-Upload API instructions
            </a>{' '}
            to upload files to this Step.
          </Trans>
        </p>
      </ModalBody>
      <ModalFooter>
        <div className='actions'>
          <button
            type='button'
            name='close'
            className='action-button button-gray'
            onClick={onClickClose}
          >
            <Trans id='js.params.Custom.UploadApiModal.footer.closeButton'>
              Close
            </Trans>
          </button>
        </div>
      </ModalFooter>
    </Modal>
  )
}
UploadApiModal.propTypes = {
  workflowId: PropTypes.number.isRequired,
  stepSlug: PropTypes.string.isRequired,
  onClickClose: PropTypes.func.isRequired // () => undefined
}

const mapDispatchToProps = { getApiToken, clearApiToken, resetApiToken }
export default connect(null, mapDispatchToProps)(UploadApiModal)
