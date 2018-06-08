import React from 'react'
import PropTypes from 'prop-types'

/**
 * Return true if popup is pointed at an oauth-success page.
 */
const isOauthFinished = (popup) => {
  try {
    if (!/^\/oauth\/?/.test(popup.location.pathname)) {
      // We're at the wrong URL.
      return false
    }
  } catch (_) {
    // We're cross-origin. That's certainly the wrong URL.
    return false
  }

  return popup.document.querySelector('p.success')

  // If p.success is not present, the server has not indicated success.
  // That means one of the following:
  // 1) error message
  // 2) request has not completed
  // ... in either case, oauth is not finished
}

export default class GoogleConnect extends React.PureComponent {
  static propTypes = {
    paramId: PropTypes.number.isRequired,
    api: PropTypes.shape({
      paramOauthDisconnect: PropTypes.func.isRequired, // func(paramId) => Promise[HttpResponse]
    }).isRequired,
    secretName: PropTypes.string,
  }

  constructor(props) {
    super(props);
    this.disconnect = this.disconnect.bind(this);
  }

  startOauth = () => {
    const popup = window.open(
      `/api/parameters/${this.props.paramId}/oauth_authorize`,
      'workbench-oauth',
      'height=500,width=400'
    )
    if (!popup) {
      console.error('Could not open auth popup')
      return
    }

    // Watch the popup incessantly, and close it when the user is done with it
    const interval = window.setInterval(() => {
      if (!popup || popup.closed || isOauthFinished(popup)) {
        if (popup && !popup.closed) popup.close()
        window.clearInterval(interval);
      }
    }, 100)
  }

  disconnect = () => {
    this.props.api.paramOauthDisconnect(this.props.paramId)
      .catch(console.error)
  }

  render () {
    let { secretName } = this.props

    let contents
    if (secretName !== null) {
      contents = (
        <React.Fragment>
          <p className="secret-name">{secretName}</p>
          <button className='disconnect' onClick={this.disconnect}>Disconnect account</button>
        </React.Fragment>
      )
    } else {
      contents = (
        <button className='connect' onClick={this.startOauth}>Connect account</button>
      )
    }

    return(
      <div className="google-connect-parameter">
        {contents}
      </div>
    )
  }
}
