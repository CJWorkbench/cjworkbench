import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import ShareUrl from '../components/ShareUrl'
import FacebookIcon from '../../icons/facebook.svg'
import TwitterIcon from '../../icons/twitter.svg'

export default function ShareableLink (props) {
  const { title, url, isPublic, logShare, component: Component = 'div' } = props
  const shareText = t({
    id: 'js.ShareModal.Url.socialLinks.shareText',
    comment:
      'The parameter will be a mention to workbench account (i.e. "@cjworkbench")',
    message: 'Check out this chart I made using {workbenchMention}:',
    values: { workbenchMention: '@workbenchdata' }
  })
  const facebookUrl = `https://www.facebook.com/sharer.php?u=${encodeURIComponent(url)}`
  const twitterUrl = `https://www.twitter.com/share?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`

  const handleClickFacebook = React.useCallback(() => logShare('Facebook'), [logShare])
  const handleClickTwitter = React.useCallback(() => logShare('Twitter'), [logShare])

  return (
    <Component className='shareable-link'>
      <strong>{title}</strong>
      <ShareUrl url={url} />
      {isPublic
        ? [
          <a
            key='twitter'
            href={twitterUrl}
            onClick={handleClickTwitter}
            className='twitter-share'
            target='_blank'
            rel='noopener noreferrer'
          >
            <TwitterIcon />
            <Trans id='js.ShareModal.Url.socialLinks.twitter'>Share</Trans>
          </a>,
          <a
            key='facebook'
            href={facebookUrl}
            onClick={handleClickFacebook}
            className='facebook-share'
            target='_blank'
            rel='noopener noreferrer'
          >
            <FacebookIcon />
            <Trans id='js.ShareModal.Url.socialLinks.facebook'>Share</Trans>
          </a>
          ]
        : null}
    </Component>
  )
}
ShareableLink.propTypes = {
  title: PropTypes.string.isRequired, // already i18n-ized
  url: PropTypes.string.isRequired, // e.g., `/workflows/1`
  isPublic: PropTypes.bool.isRequired,
  logShare: PropTypes.func.isRequired, // func('Facebook'|'Twitter'|'URL copied') => undefined
  component: PropTypes.any
}
