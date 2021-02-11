import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import ShareUrl from '../components/ShareUrl'

export default class Url extends PureComponent {
  static propTypes = {
    isPublic: PropTypes.bool.isRequired,
    url: PropTypes.string.isRequired,
    logShare: PropTypes.func.isRequired // func('Facebook'|'Twitter'|'URL copied') => undefined
  }

  handleClickTwitter = () => {
    this.props.logShare('Twitter')
  }

  handleClickFacebook = () => {
    this.props.logShare('Facebook')
  }

  renderSocialLinks = () => {
    const { url } = this.props
    const workbenchMention = '@workbenchdata'
    const shareText = t({
      id: 'js.ShareModal.Url.socialLinks.shareText',
      comment: 'The parameter will be a mention to workbench account (i.e. "@cjworkbench")',
      message: 'Check out this chart I made using {workbenchMention}:',
      values: { workbenchMention }
    })
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

    const heading = isPublic
      ? <Trans id='js.ShareModal.Url.heading.public'>Public link (accessible to anyone)</Trans>
      : <Trans id='js.ShareModal.Url.heading.private'>Private link (only accessible to collaborators)</Trans>
    return (
      <>
        <h6 key='heading'>{heading}</h6>
        <ShareUrl url={url} />
        {isPublic ? this.renderSocialLinks() : null}
      </>
    )
  }
}
