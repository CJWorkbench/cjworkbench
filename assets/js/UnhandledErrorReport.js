import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

export function UnhandledErrorReport ({ error }) {
  if (!error) return null
  let helpText

  const bugReportText = [
    `Action: ${error.type}`,
    `Message: ${error.message}`,
    `Server message: ${error.serverError}`
  ].join('\n')

  if (typeof window.Intercom === 'function') {
    helpText = (
      <>
        Could you please help us fix it? We opened a messaging window and
        included clues our developers need to work on a fix. <em>Please
        send the message</em> and then add extra details about what you
        were doing before you ran into this bug.
      </>
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
    const url = 'mailto:hello@workbenchdata.com'
      + '?subject=' + encodeURIComponent('I encountered an error')
      + '&body=' + encodeURIComponent([
        'Hi there,',
        'I encountered an error while I was using Workbench.',
        '[PLEASE DESCRIBE WHAT YOU WERE DOING HERE]',
        'Debugging details (for Workbench developers):\n' + bugReportText
      ].join('\n\n'))
    helpText = (
      <>
        Could you please help us fix it? Please email <a
        href={url} target='_blank'>hello@workbenchdata.com</a>. (Debugging
        details will be included in the message.) It helps if you describe
        what you were doing before you ran into the bug.
      </>
    )
  }

  return (
    <div className='unhandled-error-report'>
      <div className='content'>
        <h2>Oops! Our bad…</h2>
        <p>Workbench encountered an error. It’s not your fault.</p>
        <p className='help-us-debug'>{helpText}</p>
        <p>You may refresh this page to return to your Workflow.</p>
        <p>Debugging details (for our developers):</p>
        <pre>{bugReportText}</pre>
        <div className='actions'>
          <button type='button' onClick={() => window.location.reload()}>
            Refresh page
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
    serverError: PropTypes.string, // error from server, if there is one
  }) // null unless there's an error
}

function mapStateToProps (state) {
  return {
    error: state.firstUnhandledError
  }
}

export default connect(mapStateToProps)(UnhandledErrorReport)
