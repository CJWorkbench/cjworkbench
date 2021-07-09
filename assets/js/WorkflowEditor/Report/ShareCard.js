import PropTypes from 'prop-types'
import ShareButton from '../../ShareModal/ShareButton'
import { Trans } from '@lingui/macro'
import ShareUrl from '../../components/ShareUrl'

function SharingStatus ({ secretId, isPublic }) {
  if (isPublic) {
    return <Trans id='js.Report.ShareCard.sharingStatus.public'>This workflow is public</Trans>
  }
  if (secretId) {
    return <Trans id='js.Report.ShareCard.sharingSTatus.secret'>This workflow has a secret link</Trans>
  }
  return <Trans id='js.Report.ShareCard.sharingStatus.private'>This workflow is private</Trans>
}

function AccessibilityDescription ({ secretId, isPublic }) {
  if (isPublic) {
    return <Trans id='js.Report.ShareCard.accessibilityDescription.public'>Anyone on the Internet can view this report</Trans>
  }
  if (secretId) {
    return <Trans id='js.Report.ShareCard.accessibilityDescription.secret'>Anyone with the link can view this report</Trans>
  }
  return <Trans id='js.Report.ShareCard.accessibilityDescription.private'>Only collaborators can view this report</Trans>
}

export default function ShareCard ({ workflowId, secretId, isPublic }) {
  const url = (!isPublic && secretId)
    ? `${window.origin}/workflows/${secretId}/report`
    : `${window.origin}/workflows/${workflowId}/report`

  return (
    <aside className='share-card'>
      <div>
        <h4>
          <SharingStatus secretId={secretId} isPublic={isPublic} />
        </h4>
        <div className='workflow-public'>
          <p className='accessible-to'>
            <AccessibilityDescription secretId={secretId} isPublic={isPublic} />
          </p>
          <ShareButton>
            <Trans
              id='js.Report.ShareCard.editPrivacy.sharebutton'
              comment="As in 'Edit privacy settings'"
            >
              Edit privacy
            </Trans>
          </ShareButton>
        </div>
      </div>
      <div>
        <h4>
          <Trans
            id='js.Report.ShareCard.reportUrl.header'
            comment="As in 'URL of report'"
          >
            Report URL
          </Trans>
        </h4>
        <ShareUrl url={url} go />
      </div>
    </aside>
  )
}
ShareCard.propTypes = {
  workflowId: PropTypes.number.isRequired,
  secretId: PropTypes.string.isRequired,
  isPublic: PropTypes.bool.isRequired
}
