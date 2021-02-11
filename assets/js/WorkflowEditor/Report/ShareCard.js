import PropTypes from 'prop-types'
import ShareButton from '../../ShareModal/ShareButton'
import { Trans } from '@lingui/macro'
import ShareUrl from '../../components/ShareUrl'

export default function ShareCard ({ workflowId, isPublic }) {
  return (
    <aside className='share-card'>
      <div>
        <h4>
          {isPublic ? (
            <Trans id='js.Report.ShareCard.sharingStatus.public'>This workflow is public</Trans>
          ) : (
            <Trans id='js.Report.ShareCard.sharingStatus.private'>This workflow is private</Trans>
          )}
        </h4>
        <div className='workflow-public'>
          <p className='accessible-to'>
            {isPublic ? (
              <Trans id='js.Report.ShareCard.accessibilityDescription.public'>Anyone can view this report</Trans>
            ) : (
              <Trans id='js.Report.ShareCard.accessibilityDescription.private'>Only collaborators can view this report</Trans>
            )}
          </p>
          <ShareButton>
            <Trans id='js.Report.ShareCard.editPrivacy.sharebutton' comment="As in 'Edit privacy settings'">Edit privacy</Trans>
          </ShareButton>
        </div>
      </div>
      <div>
        <h4><Trans id='js.Report.ShareCard.reportUrl.header' comment="As in 'URL of report'">Report Sharing URL</Trans></h4>
        <ShareUrl url={`${window.location.origin}/workflows/${workflowId}/report`} go />
      </div>
    </aside>
  )
}
ShareCard.propTypes = {
  workflowId: PropTypes.number.isRequired,
  isPublic: PropTypes.bool.isRequired
}
