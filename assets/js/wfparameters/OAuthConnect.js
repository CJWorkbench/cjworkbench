import React from 'react'
import PropTypes from 'prop-types'

export default class OAuthConnect extends React.PureComponent {
  static propTypes = {
    paramIdName: PropTypes.string.isRequired,
    startCreateSecret: PropTypes.func.isRequired, // func(paramIdName) => undefined
    deleteSecret: PropTypes.func.isRequired, // func(paramIdName) => undefined
    secretName: PropTypes.string,
  }

  startCreateSecret = () => {
    const { paramIdName, startCreateSecret } = this.props
    startCreateSecret(paramIdName)
  }

  deleteSecret = () => {
    const { paramIdName, deleteSecret } = this.props
    deleteSecret(paramIdName)
  }

  render () {
    let { secretName } = this.props

    let contents
    if (secretName !== null) {
      contents = (
        <React.Fragment>
          <p className="secret-name">{secretName}</p>
          <button className='disconnect' onClick={this.deleteSecret}>Sign out</button>
        </React.Fragment>
      )
    } else {
      contents = (
        <button className='connect' onClick={this.startCreateSecret}>Connect account</button>
      )
    }

    return(
      <div className="oauth-connect-parameter">
        {contents}
      </div>
    )
  }
}
