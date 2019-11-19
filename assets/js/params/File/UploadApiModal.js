import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../components/Modal'
import { getApiToken, clearApiToken, resetApiToken } from './actions'
import { connect } from 'react-redux'
import { Trans } from '@lingui/macro'
import { hideFromTrans } from '../../i18n/messages'

class ApiTokenState {
  constructor (flag, apiToken) {
    this.flag = flag
    this.apiToken = apiToken
  }
}
ApiTokenState.OK = 0
ApiTokenState.LOADING = 1
ApiTokenState.SENDING = 2

function ApiToken ({ workflowId, wfModuleSlug, apiTokenState, clearApiToken, resetApiToken }) {
  switch (apiTokenState.flag) {
    case ApiTokenState.OK: return <ApiTokenOk workflowId={workflowId} wfModuleSlug={wfModuleSlug} apiToken={apiTokenState.apiToken} clearApiToken={clearApiToken} resetApiToken={resetApiToken} />
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

function ApiTokenOk ({ workflowId, wfModuleSlug, apiToken, clearApiToken, resetApiToken }) {
  return (
    <div className='state-ok'>
      {apiToken ? (
        <>
          <p className='api-token'>
            <strong><Trans id='js.params.File.UploadApiModal.ApiTokenOk.apiToken'>API Token</Trans></strong>:
            <code>{apiToken}</code>
            <button type='button' name='reset-api-token' onClick={resetApiToken}><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.resetApiToken'>Reset API token</Trans></button>
            <button type='button' name='clear-api-token' onClick={clearApiToken}><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.disableApi'>Disable API</Trans></button>
          </p>
          <p className='workflow-id'>
            <strong><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.workflowId'>Workflow ID</Trans></strong>:
            <code>{workflowId}</code>
          </p>
          <p className='step-slug'>
            <strong><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.stepId'>Step ID</Trans></strong>:
            <code>{wfModuleSlug}</code>
          </p>
        </>
      ) : (
        <p className='no-api-token'>
          <span><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.noApiToken'>No API token</Trans></span>
          <button type='button' name='reset-api-token' onClick={resetApiToken}><Trans id='js.params.Custom.UploadApiModal.ApiTokenOk.enableApi'>Enable API</Trans></button>
        </p>
      )}
    </div>
  )
}

function Instructions ({ workflowId, wfModuleSlug, apiToken }) {
  const varsCode = [
    `WorkflowId = "${workflowId}"`,
    `StepId = "${wfModuleSlug}"`,
    `ApiToken = "${apiToken}"`,
    'FileToUpload = "/path/to/test.csv"',
    'Filename = "test.csv"  # name that appears in Workbench'
  ].join('\n')

  const importsCode = [
    'import boto3',
    'import botocore',
    'import requests'
  ].join('\n')

  const postUrl = `${window.location.origin}/api/v1/workflows/{WorkflowId}/steps/{StepId}/uploads`

  const postCode = [
    `credentials_url = f"${postUrl}"`,
    'credentials_response = requests.post(',
    '    credentials_url,',
    '    headers={"Authorization": f"Bearer {ApiToken}"}',
    ')',
    'credentials_response.raise_for_status()  # expect 200 OK',
    's3_config = credentials_response.json()'
  ].join('\n')

  const uploadCode = [
    's3_client = boto3.client(',
    '    \'s3\',',
    '    aws_access_key_id=s3_config["credentials"]["accessKeyId"],',
    '    aws_secret_access_key=s3_config["credentials"]["secretAccessKey"],',
    '    aws_session_token=s3_config["credentials"]["sessionToken"],',
    '    region_name=s3_config["region"],',
    '    endpoint_url=s3_config["endpoint"],',
    '    config=botocore.client.Config(s3={"addressing_style": "path"}),',
    ')',
    's3_client.upload_file(FileToUpload, s3_config["bucket"], s3_config["key"])'
  ].join('\n')

  const finishCode = [
    'finish_response = requests.post(',
    '    s3_config["finishUrl"],',
    '    headers={"Authorization": f"Bearer {ApiToken}"},',
    '    json={"filename": Filename},',
    ')',
    'finish_response.raise_for_status()  # expect 200 OK'
  ].join('\n')

  return (
    <>
      <h5><Trans id='js.params.Custom.UploadApiModal.Instructions.title'>How to upload</Trans></h5>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.eachFileBelongs' description='The tag is a link to Amazon s3'>
          Each file you upload belongs in a unique <a href='https://aws.amazon.com/s3/'>Amazon S3</a>-compatible endpoint. You cannot reuse the same endpoint for two files: to replace a file, you must follow all these steps again.
        </Trans>
      </p>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.theseInstructionsUsepython'>
          These instructions use Python 3, for illustration. You may use any programming language.
        </Trans>
      </p>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.goodWaytoStart'>
          A good way to start your project is to copy and paste all this code into a script (one step at a time), and then edit.
        </Trans>
      </p>
      <h6>0. <Trans id='js.params.Custom.UploadApiModal.Instructions.dependencies.title'>Install and load dependencies</Trans></h6>
      <p><Trans id='js.params.Custom.UploadApiModal.Instructions.dependencies.yourProgramWillneed'>Your program will need to make HTTP requests and upload to S3.</Trans></p>
      <pre>{importsCode}</pre>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.dependencies.boto3' description='The tags are links to external info. The parameter is the name of a library.'>
          <a href='https://aws.amazon.com/sdk-for-python/'>{hideFromTrans('boto3')}</a> is the AWS SDK for Python. There is an <a href='https://aws.amazon.com/tools/'>AWS SDK</a> for most any programming language; and there are dozens of third-party libraries that are compatible with Workbench. Use any library that supports custom endpoints, session tokens and "path" addressing style.
        </Trans>
      </p>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.dependencies.requestsHttpLib' description='The tags are links to external info. The parameters are names of libraries.'>
          <a href='https://2.python-requests.org/en/master/'>{hideFromTrans('requests')}</a> is an HTTP library with simpler requests than Python's built-in <a href='https://docs.python.org/3/library/urllib.request.html'>{hideFromTrans('urllib.request')}</a>.
        </Trans>
      </p>
      <h6>1. <Trans id='js.params.Custom.UploadApiModal.Instructions.storeVariablesAndsecrets.title'>Store variables and secrets</Trans></h6>
      <pre>{varsCode}</pre>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.storeVariablesAndsecrets.notShareApitoken' description='The tag adds emphasis'>
          <strong>Do not share the API token or commit it to any code repository.</strong> Anybody with access to the token can alter this step. Keep it safe. If you suspect your API token has been compromised, reset the API token.
        </Trans>
      </p>
      <h6>1. <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.title'>Query Workbench for upload credentials</Trans></h6>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.postRequest' description='The parameters contain code. The tags wrap them for correct presentation.'>
        Send an HTTP POST request to <code>{postUrl}</code>. It should have no parameters or content. (Do not upload the file to this URL.) It must have an <code>{hideFromTrans('Authorization')}</code> header that looks like <code>{hideFromTrans('Bearer [ApiToken]')}</code>.
        </Trans>
      </p>
      <pre>{postCode}</pre>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.root' description='The parameter contains code. The tag wraps it for correct presentation.'>
          <code>{hideFromTrans('s3_config')}</code> will be a dictionary with the following keys:
        </Trans>
      </p>
      <ul>
        <li><code>endpoint</code>:
          <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.endpoint'>
            URL of S3-compatible upload server
          </Trans>
        </li>
        <li><code>region</code>:
          <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.region'>
            S3-compatible region code
          </Trans>
        </li>
        <li><code>bucket</code>:
          <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.bucket'>
            S3 bucket name where your file should be uploaded
          </Trans>
        </li>
        <li><code>key</code>: <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.key'>S3 key name where your file should be uploaded</Trans></li>
        <li><code>credentials</code>:
          <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.credentials' description='The parameters contain code. The tags wrap them for correct presentation.'>
            Dictionary with <code>{hideFromTrans('accessKeyId')}</code>, <code>{hideFromTrans('secretAccessKey')}</code> and <code>{hideFromTrans('sessionToken')}</code> keys
          </Trans>
        </li>
        <li><code>finishUrl</code>: <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.s3Config.finishUrl'>(non-S3) URL to notify when we're done using the S3 API</Trans></li>
      </ul>
      <p>
        <Trans id='js.params.Custom.UploadApiModal.Instructions.queryWorkbenchForUploadCreds.theCredsAllowBucketKey' description="The parameters are 'bucket' and 'key' respectively. The tags wrap them for correct presentation.">
          The credentials will only allow you to upload your file to the specified <code>{hideFromTrans('bucket')}</code> and <code>{hideFromTrans('key')}</code>. The credentials will expire in a few hours.
        </Trans>
      </p>
      <h6>2. <Trans id='js.params.Custom.UploadApiModal.Instructions.uploadS3CompatibleBucket.title'>Upload to S3-compatible bucket</Trans></h6>
      <pre>{uploadCode}</pre>
      <p><Trans id='js.params.Custom.UploadApiModal.Instructions.uploadS3CompatibleBucket.seeAwsSdkDocumentation' description='The tag is a URL to external info'>See the <a href='https://aws.amazon.com/tools/'>AWS SDK documentation</a> for your library to learn how to upload a file.</Trans></p>
      <h6>3. <Trans id='js.params.Custom.UploadApiModal.Instructions.finishUploadAndGiveFilename'>Tell Workbench to finish the upload, and give it a filename</Trans></h6>
      <pre>{finishCode}</pre>
      <p><Trans id='js.params.Custom.UploadApiModal.Instructions.finishUploadAndGiveFilename.workflowUploadModal'>In your workflow, this Step will be updated to use the new file.</Trans></p>
    </>
  )
}

export const UploadApiModal = React.memo(function UploadApiModal ({ wfModuleId, wfModuleSlug, workflowId, onClickClose, getApiToken, resetApiToken, clearApiToken }) {
  const [apiTokenState, setApiTokenState] = React.useState(new ApiTokenState(ApiTokenState.LOADING, null))
  const { apiToken } = apiTokenState
  React.useEffect(() => {
    getApiToken(wfModuleId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken)))
  }, [wfModuleId])
  const doResetApiToken = React.useCallback(() => {
    setApiTokenState(new ApiTokenState(ApiTokenState.SENDING, apiTokenState.apiToken))
    resetApiToken(wfModuleId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, apiToken)))
  })
  const doClearApiToken = React.useCallback(() => {
    setApiTokenState(new ApiTokenState(ApiTokenState.SENDING, null))
    clearApiToken(wfModuleId).then(({ value }) => value).then(apiToken => setApiTokenState(new ApiTokenState(ApiTokenState.OK, null)))
  })

  return (
    <Modal className='upload-api-modal' isOpen size='lg' toggle={onClickClose}>
      <ModalHeader><Trans id='js.params.Custom.UploadApiModal.header.title' description='This should be all-caps for styling reasons'>UPLOAD BY API</Trans></ModalHeader>
      <ModalBody>
        <h5><Trans id='js.params.Custom.UploadApiModal.programmerInstructions'>These instructions are for programmers.</Trans></h5>
        <p><Trans id='js.params.Custom.UploadApiModal.theFileUploadApiIsPerfect'>The file-upload API is perfect for loading data from cronjobs or other external scripts. You can send data to Workbench using any programming language.</Trans></p>
        {apiToken ? (
          <p><Trans id='js.params.Custom.UploadApiModal.fileuploadApiStatus.enabled' description='The tag adds emphasis'>The file-upload API is <strong>enabled</strong>.</Trans></p>
        ) : (
          <p><Trans id='js.params.Custom.UploadApiModal.fileuploadApiStatus.disabled'>The file-upload API is disabled. Please enable it to allow uploading.</Trans></p>
        )}
        <ApiToken
          workflowId={workflowId}
          wfModuleSlug={wfModuleSlug}
          apiTokenState={apiTokenState}
          resetApiToken={doResetApiToken}
          clearApiToken={doClearApiToken}
        />
        {apiToken ? (
          <Instructions workflowId={workflowId} wfModuleSlug={wfModuleSlug} apiToken={apiToken} />
        ) : null}
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
  wfModuleId: PropTypes.number.isRequired,
  wfModuleSlug: PropTypes.string.isRequired,
  onClickClose: PropTypes.func.isRequired // () => undefined
}

const mapDispatchToProps = { getApiToken, clearApiToken, resetApiToken }
export default connect(null, mapDispatchToProps)(UploadApiModal)
