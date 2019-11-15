import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

class Url extends React.PureComponent {
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

  handleClickCopy = () => {
    const { logShare, url } = this.props

    logShare('URL copied')

    this.setState(state => ({ nTimesCopied: state.nTimesCopied + 1 }))
    navigator.clipboard.writeText(url)
  }

  handleClickTwitter = () => {
    this.props.logShare('Twitter')
  }

  handleClickFacebook = () => {
    this.props.logShare('Facebook')
  }

  renderSocialLinks = () => {
    const { url, i18n } = this.props
    const workbenchMention = '@workbenchdata'
    const shareText = i18n._(
      /* i18n: The parameter will be a mention to workbench account (i.e. "@cjworkbench") */
      t('js.ShareModal.Url.socialLinks.shareText')`Check out this chart I made using ${workbenchMention}:`
    )
    const facebookUrl = `https://www.facebook.com/sharer.php?u=${encodeURIComponent(url)}`
    const twitterUrl = `https://www.twitter.com/share?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`

    return (
      <div key='share' className='share-links'>
        <a href={twitterUrl} onClick={this.handleClickTwitter} className='twitter-share' target='_blank' rel='noopener noreferrer'>
          <i className='icon-twitter' />
          <Trans id='js.ShareModal.Url.socialLinks.twitter'>Share</Trans>
        </a>

        <a href={facebookUrl} onClick={this.handleClickFacebook} className='facebook-share' target='_blank' rel='noopener noreferrer'>
          <i className='icon-facebook' />
          <Trans id='js.ShareModal.Url.socialLinks.facebook'>Share</Trans>
        </a>
      </div>
    )
  }

  render () {
    const { isPublic, url } = this.props
    const { nTimesCopied } = this.state

    const heading = isPublic
      ? <Trans id='js.ShareModal.Url.heading.public'>Public link (accessible to anyone)</Trans>
      : <Trans id='js.ShareModal.Url.heading.private'>Private link (only accessible to collaborators)</Trans>
    return (
      <>
        <h6 key='heading'>{heading}</h6>
        <div key='url' className='copy-url'>
          <div className='url'>{url}</div>
          <button name='copy' onClick={this.handleClickCopy}>
            <Trans id='js.ShareModal.Url.copyToClipboardButton'>Copy to clipboard</Trans>
          </button>
          {nTimesCopied > 0 ? <div className='copied-flash' key={nTimesCopied} /> : null}
        </div>
        {isPublic ? this.renderSocialLinks() : null}
      </>
    )
  }
}

export default withI18n()(Url)
