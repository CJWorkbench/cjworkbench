import React from 'react'
import PropTypes from 'prop-types'
import ShareButton from '../ShareModal/ShareButton'
import { Trans } from '@lingui/macro'

export default function ShareCard ({ workflowId, isPublic }) {
  return (
    <aside className='share-card'>
      <div className='prompt'>
        <span className='status'>
          {isPublic ? (
            <Trans id='js.Report.ShareCard.sharingStatus.public'>This workflow is public</Trans>
          ) : (
            <Trans id='js.Report.ShareCard.sharingStatus.private'>This workflow is private</Trans>
          )}
        </span>
        <p className='accessible-to'>
          {isPublic ? (
            <Trans id='js.Report.ShareCard.accessibilityDescription.public'>Anyone can view this report</Trans>
          ) : (
            <Trans id='js.Report.ShareCard.accessibilityDescription.private'>Only collaborators can view this report</Trans>
          )}
        </p>
        <ShareButton><Trans id='js.Report.ShareCard.editPrivacy.sharebutton'>Edit privacy</Trans></ShareButton>
      </div>
      <div className='url'>
        <h4><Trans id='js.Report.ShareCard.reportUrl.header'>Report URL</Trans></h4>
        <div className='copy'>
          {window.location.origin}/workflows/{workflowId}/report
        </div>
      </div>
    </aside>
  )
}
ShareCard.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired
}
