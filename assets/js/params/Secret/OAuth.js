import React from 'react'
import PropTypes from 'prop-types'

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

  startCreateSecret = () => {
    const { name, startCreateSecret } = this.props
    startCreateSecret(name)
  }

  deleteSecret = () => {
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
          <button type='button' className='disconnect' onClick={this.deleteSecret}>Sign out</button>
        </>
      )
    } else {
      contents = (
        <button type='button' className='connect' onClick={this.startCreateSecret}>Connect account</button>
      )
    }

    return (
      <div className='oauth-connect-parameter'>
        {contents}
      </div>
    )
  }
}
