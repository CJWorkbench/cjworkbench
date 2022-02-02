import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import ShareUrl from '../components/ShareUrl'
import FacebookIcon from '../../icons/facebook.svg'
import TwitterIcon from '../../icons/twitter.svg'

export default function ShareableLink (props) {
  const { title, url, isPublic, showShareHeader, component: Component = 'div' } = props
  const shareText = t({
    id: 'js.ShareModal.Url.socialLinks.shareText',
    comment:
      'The parameter will be a mention to workbench account (i.e. "@cjworkbench")',
    message: 'Check out this chart I made using {workbenchMention}:',
    values: { workbenchMention: '@workbenchdata' }
  })
  const facebookUrl = `https://www.facebook.com/sharer.php?u=${encodeURIComponent(url)}`
  const twitterUrl = `https://www.twitter.com/share?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`

  return (
    <Component className='shareable-link'>
      <h6>{title}</h6>
      <ShareUrl url={url} />
      {isPublic
        ? [
            showShareHeader
              ? (
                <strong key='header' className='share-header'>
                  <Trans id='js.ShareModal.Url.socialLinks.shareHeader'>Share</Trans>
                </strong>
                )
              : null,
          <a
            key='twitter'
            href={twitterUrl}
            className='twitter-share'
            target='_blank'
            rel='noopener noreferrer'
          >
            <TwitterIcon />
          </a>,
          <a
            key='facebook'
            href={facebookUrl}
            className='facebook-share'
            target='_blank'
            rel='noopener noreferrer'
          >
            <FacebookIcon />
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
  showShareHeader: PropTypes.bool.isRequired,
  component: PropTypes.any
}
