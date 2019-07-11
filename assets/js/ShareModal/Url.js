import React from 'react'
import PropTypes from 'prop-types'

export default class Url extends React.PureComponent {
  static propTypes = {
    isPublic: PropTypes.bool.isRequired,
    url: PropTypes.string.isRequired,
    logShare: PropTypes.func.isRequired // func('Facebook'|'Twitter'|'URL copied') => undefined
  }

  state = {
    // "flash message for 1s" logic: when nTimesCopied>0, that becomes the
    // `key` of a <div className='copied-flash'>`. That means every click, we
    // delete old divs and create a new one. We use CSS to animate the new
    // element -- first to be visible, and then to be hidden.
    nTimesCopied: 0
  }

  onClickCopy = () => {
    const { logShare, url, isPublic } = this.props

    logShare('URL copied')

    this.setState(state => ({ nTimesCopied: state.nTimesCopied + 1 }))
    navigator.clipboard.writeText(url)
  }

  onClickTwitter = () => {
    this.props.logShare('Twitter')
  }

  onClickFacebook = () => {
    this.props.logShare('Facebook')
  }

  renderSocialLinks = () => {
    const { url } = this.props
    const facebookUrl = `https://www.facebook.com/sharer.php?u=${encodeURIComponent(url)}`
    const twitterUrl = `https://www.twitter.com/share?url=${encodeURIComponent(url)}&text=${encodeURIComponent('Check out this chart I made using @cjworkbench:')}`

    return (
      <div key='share' className='share-links'>
        <a href={twitterUrl} onClick={this.onClickTwitter} className='twitter-share' target='_blank'>
          <i className='icon-twitter' />
          Share
        </a>

        <a href={facebookUrl} onClick={this.onClickFacebook} className='facebook-share' target='_blank'>
          <i className='icon-facebook' />
          Share
        </a>
      </div>
    )
  }

  render () {
    const { isPublic, url } = this.props
    const { nTimesCopied } = this.state

    const heading = isPublic ? 'Public link (accessible to anyone)' : 'Private link (only accessible to collaborators)'

    return (
      <React.Fragment>
        <h6 key='heading'>{heading}</h6>
        <div key='url' className='copy-url'>
          <div className='url'>{url}</div>
          <button name='copy' onClick={this.onClickCopy}>Copy to clipboard</button>
          {nTimesCopied > 0 ? <div className='copied-flash' key={nTimesCopied} /> : null}
        </div>
        {isPublic ? this.renderSocialLinks() : null}
      </React.Fragment>
    )
  }
}
