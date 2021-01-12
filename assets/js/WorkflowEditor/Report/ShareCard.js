import React from 'react'
import PropTypes from 'prop-types'
import ShareButton from '../../ShareModal/ShareButton'
import { Trans } from '@lingui/macro'

export default function ShareCard ({ workflowId, isPublic }) {
  return (
    <aside className='share-card'>
      <div className='prompt'>
        <div className='status'>
          <h4 className='title'>
            {isPublic ? (
              <Trans id='js.Report.ShareCard.sharingStatus.public'>This workflow is public</Trans>
            ) : (
              <Trans id='js.Report.ShareCard.sharingStatus.private'>This workflow is private</Trans>
            )}
          </h4>
          <p className='accessible-to'>
            {isPublic ? (
              <Trans id='js.Report.ShareCard.accessibilityDescription.public'>Anyone can view this report</Trans>
            ) : (
              <Trans id='js.Report.ShareCard.accessibilityDescription.private'>Only collaborators can view this report</Trans>
            )}
          </p>
        </div>
        <ShareButton><Trans id='js.Report.ShareCard.editPrivacy.sharebutton' comment="As in 'Edit privacy settings'">Edit privacy</Trans></ShareButton>
      </div>
      <div className='url'>
        <div className='title'>
          <h4><Trans id='js.Report.ShareCard.reportUrl.header' comment="As in 'URL of report'">Report URL</Trans></h4>
          <p>Share report with collaborators</p>
        </div>git st
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
