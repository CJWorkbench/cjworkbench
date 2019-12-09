import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Trans } from '@lingui/macro'

export function UnhandledErrorReport ({ error }) {
  if (!error) return null
  let helpText

  const bugReportText = [
    `URL: ${String(window.location)}`,
    `Action: ${error.type}`,
    `Message: ${error.message}`,
    `Server message: ${error.serverError}`
  ].join('\n')

  if (typeof window.Intercom === 'function') {
    helpText = (
      <ol>
        <li><Trans id='js.UnhandledErrorReport.Intercom.helpText.weOpenedAWindow' description='The tag adds emphasis'>We opened a messaging window and included details for our developers to fix the issue. <em>Please send the message</em>.</Trans></li>
        <li><Trans id='js.UnhandledErrorReport.helpText.pleaseDescribeYourActions'>It helps if you can describe what you were doing before you ran into the bug.</Trans></li>
      </ol>
    )
    React.useEffect(() => {
      window.Intercom(
        'showNewMessage',
        [
          'Could you please help me with this bug?',
          'Debugging details (for developers):',
          bugReportText
        ].join('\n')
      )
    }, [])
  } else {
    const email = 'hello@workbenchdata.com'
    const url = `mailto:${email}` +
      '?subject=' + encodeURIComponent('I encountered an error') +
      '&body=' + encodeURIComponent([
        'Hi there,',
        'I encountered an error while I was using Workbench.',
        '[PLEASE DESCRIBE WHAT YOU WERE DOING HERE]',
        'Debugging details (for Workbench developers):\n' + bugReportText
      ].join('\n\n'))
    helpText = (
      <ol>
        <li>
          <Trans id='js.UnhandledErrorReport.helpText.debuggingDetails' description="The parameter is an email address and the tag is a 'mailto:' url">
                Copy the debugging details below and send them to <a href={url} target='_blank' rel='noopener noreferrer'>{email}</a>.
          </Trans>
        </li>
        <li>
          <Trans id='js.UnhandledErrorReport.helpText.pleaseDescribeYourActions'>
                It helps if you can describe what you were doing before you ran into the bug.
          </Trans>
        </li>
      </ol>
    )
  }

  return (
    <div className='unhandled-error-report'>
      <div className='content'>
        <h2><Trans id='js.UnhandledErrorReport.content.oops'>Oops! Something isn't right.</Trans></h2>
        <p><Trans id='js.UnhandledErrorReport.content.pleaseFollowSteps'>Please follow these simple steps to help us fix the issue.</Trans></p>
        <div className='help-us-debug'>{helpText}</div>
        <p><Trans id='js.UnhandledErrorReport.content.thankYou'>THANK YOU! Refresh this page to return to your Workflow.</Trans></p>
        <p><Trans id='js.UnhandledErrorReport.content.debuggingDetails'>Debugging details (please send):</Trans></p>
        <pre>{bugReportText}</pre>
        <div className='actions'>
          <button type='button' onClick={() => window.location.reload()}>
            <Trans id='js.UnhandledErrorReport.actions.refreshPageButton'>Refresh page</Trans>
          </button>
        </div>
      </div>
    </div>
  )
}
UnhandledErrorReport.propTypes = {
  error: PropTypes.shape({
    type: PropTypes.string.isRequired, // Redux action name
    message: PropTypes.string.isRequired, // Error.toString() retval
    serverError: PropTypes.string // error from server, if there is one
  }) // null unless there's an error
}

function mapStateToProps (state) {
  return {
    error: state.firstUnhandledError
  }
}

export default connect(mapStateToProps)(UnhandledErrorReport)
