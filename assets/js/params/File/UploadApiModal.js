import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../components/Modal'
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

function ApiToken ({ workflowId, stepSlug, apiTokenState, clearApiToken, resetApiToken }) {
  switch (apiTokenState.flag) {
    case ApiTokenState.OK: return <ApiTokenOk workflowId={workflowId} stepSlug={stepSlug} apiToken={apiTokenState.apiToken} clearApiToken={clearApiToken} resetApiToken={resetApiToken} />
    case ApiTokenState.LOADING: return <ApiTokenLoading />
    case ApiTokenState.SENDING: return <ApiTokenSending />
  }
}

function ApiTokenLoading () {
  return <div className='state-loading'><Trans id='js.params.File.UploadApiModal.ApiTokenLoading'>Loading</Trans></div>
}

function ApiTokenSending () {
  return <div className='state-sending'>…</div>
}

function ApiTokenOk ({ workflowId, stepSlug, apiToken, clearApiToken, resetApiToken }) {
  const createFileUrl = `${window.location.origin}/api/v1/workflows/${workflowId}/steps/${stepSlug}/files`

  return (
    <div className='state-ok'>
      {apiToken ? (
        <>
          <p className='actions'>
            <button
              type='button'
              name='reset-api-token'
              onClick={resetApiToken}
            >
              <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.resetApiToken'>Reset API token</Trans>
            </button>
            <button
              type='button'
              name='clear-api-token'
              onClick={clearApiToken}
            >
              <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.disableApi'>Disable API</Trans>
            </button>
          </p>
          <dl>
            <dt><Trans id='js.params.File.UploadApiModal.ApiTokenOk.createFileUrl'>Create-file URL</Trans></dt>
            <dd>{createFileUrl}</dd>
            <dt><Trans id='js.params.File.UploadApiModal.ApiTokenOk.apiToken'>API Token</Trans></dt>
            <dd>{apiToken}</dd>
          </dl>
          <p>
            <Trans id='js.params.File.UploadApiModal.ApiTokenOk.instructions'>Follow our <a href='https://github.com/CJWorkbench/cjworkbench/wiki/File-Upload-API' target='_blank' rel='noopener noreferrer'>File-Upload API instructions</a> to upload files to this Step.</Trans>
          </p>
        </>
      ) : (
        <p className='no-api-token'>
          <span><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.noApiToken'>No API token</Trans></span>
          <button
            type='button'
            name='reset-api-token'
            onClick={resetApiToken}
          >
            <Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.enableApi'>Enable API</Trans>
          </button>
        </p>
      )}
    </div>
  )
}

export const UploadApiModal = React.memo(function UploadApiModal ({ stepId, stepSlug, workflowId, onClickClose, getApiToken, resetApiToken, clearApiToken }) {
  const [apiTokenState, setApiTokenState] = React.useState(new ApiTokenState(ApiTokenState.LOADING, null))
  const { apiToken } = apiTokenState
  React.useEffect(() => {
    getApiToken(stepId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken)))
  }, [stepId])
  const doResetApiToken = React.useCallback(() => {
    setApiTokenState(new ApiTokenState(ApiTokenState.SENDING, apiTokenState.apiToken))
    resetApiToken(stepId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken)))
  })
  const doClearApiToken = React.useCallback(() => {
    setApiTokenState(new ApiTokenState(ApiTokenState.SENDING, null))
    clearApiToken(stepId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, null)))
  })

  return (
    <Modal className='upload-api-modal' isOpen size='lg' toggle={onClickClose}>
      <ModalHeader><Trans id='js.params.Custom.UploadApiModal.header.title' comment='This should be all-caps for styling reasons'>UPLOAD BY API</Trans></ModalHeader>
      <ModalBody>
        <h5><Trans id='js.params.Custom.UploadApiModal.programmerInstructions'>These instructions are for programmers.</Trans></h5>
        <p><Trans id='js.params.Custom.UploadApiModal.theFileUploadApiIsPerfect'>The file-upload API is perfect for loading data from cronjobs or other external scripts. You can send data to Workbench using any programming language.</Trans></p>
        {apiToken ? (
          <p><Trans id='js.params.Custom.UploadApiModal.fileuploadApiStatus.enabled' comment='The tag adds emphasis'>The file-upload API is <strong>enabled</strong>.</Trans></p>
        ) : (
          <p><Trans id='js.params.Custom.UploadApiModal.fileuploadApiStatus.disabled'>The file-upload API is disabled. Please enable it to allow uploading.</Trans></p>
        )}
        <ApiToken
          workflowId={workflowId}
          stepSlug={stepSlug}
          apiTokenState={apiTokenState}
          resetApiToken={doResetApiToken}
          clearApiToken={doClearApiToken}
        />
      </ModalBody>
      <ModalFooter>
        <div className='actions'>
          <button
            name='close'
            className='action-button button-gray'
            onClick={onClickClose}
          ><Trans id='js.params.Custom.UploadApiModal.footer.closeButton'>Close</Trans>
          </button>
        </div>
      </ModalFooter>
    </Modal>
  )
})
UploadApiModal.propTypes = {
  workflowId: PropTypes.number.isRequired,
  stepId: PropTypes.number.isRequired,
  stepSlug: PropTypes.string.isRequired,
  onClickClose: PropTypes.func.isRequired // () => undefined
}

const mapDispatchToProps = { getApiToken, clearApiToken, resetApiToken }
export default connect(null, mapDispatchToProps)(UploadApiModal)
