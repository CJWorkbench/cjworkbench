import React from 'react'
import PropTypes from 'prop-types'
import { Trans,t } from '@lingui/macro'
import { withI18n,I18n } from '@lingui/react'

export default class OAuth extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    secretMetadata: PropTypes.shape({
      name: PropTypes.string.isRequired
    }), // null if not set
    startCreateSecret: PropTypes.func.isRequired, // func(name) => undefined
    deleteSecret: PropTypes.func.isRequired, // func(name) => undefined
    secretLogic: PropTypes.shape({
      service: PropTypes.oneOf(['google', 'intercom', 'twitter'])
    })
  }

  handleClickConnect = () => {
    const { name, startCreateSecret } = this.props
    startCreateSecret(name)
  }

  handleClickDisconnect = () => {
    const { name, deleteSecret } = this.props
    deleteSecret(name)
  }

  render () {
    const { secretMetadata } = this.props

    let contents
    if (secretMetadata) {
      contents = (
        <>
          <p className='secret-name'>{secretMetadata.name}</p>
          <button type='button' className='disconnect' onClick={this.handleClickDisconnect}><Trans id="OAuth.signout">Sign out</Trans></button>
        </>
      )
    } else {
      contents = (
        <button type='button' className='connect' onClick={this.handleClickConnect}><Trans id="OAuth.connectaccount">Connect account</Trans></button>
      )
    }

    return (
      <div className='oauth-connect-parameter'>
        {contents}
      </div>
    )
  }
}
