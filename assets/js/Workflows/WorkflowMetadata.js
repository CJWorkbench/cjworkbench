// WorkflowMetadata: that line below the workflow title
// which shows owner, last modified date, public/private

import React from 'react'
import PropTypes from 'prop-types'
import { timeDifference } from '../utils'
import { withI18n } from '@lingui/react'
import { t, Trans } from '@lingui/macro'

export class WorkflowMetadata extends React.Component {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    workflow: PropTypes.object.isRequired,
    openShareModal: PropTypes.func.isRequired, // func(workflowId) => undefined
    test_now: PropTypes.object // optional injection for testing, avoid time zone issues for Last Update time
  }

  handleClickOpenShareModal = (ev) => {
    // On the Workflows page, this button is rendered within an <a>. Make sure
    // the browser's usual <a> handling doesn't happen.
    ev.preventDefault()
    ev.stopPropagation()

    // Grab workflow ID -- WorkflowMetadata appears on the "workflows" page,
    // which can have several workflows.
    this.props.openShareModal(this.props.workflow.id)
  }

  render () {
    const now = this.props.test_now || new Date()
    const owner = this.props.workflow.owner_name.trim()
    const timeAgo = timeDifference(this.props.workflow.last_update, now, this.props.i18n)

    // don't show author if this workflow is anonymous
    const attribution = !this.props.workflow.is_anonymous ? (
      <li className='attribution'>
        <span className='metadata'>
          <Trans id='js.Workflows.WorkflowMetadata.owner'>by {owner}</Trans>
        </span>
        <span className='separator'>-</span>
      </li>
    ) : null

    const modalLink = !(this.props.workflow.read_only || this.props.workflow.is_anonymous) ? (
      <li>
        <span className='separator'>-</span>
        <button type='button' className='public-private' title={this.props.i18n._(t('js.Workflows.WorkflowMetadata.changePrivacy.button')`Change privacy`)} onClick={this.handleClickOpenShareModal}>
          {this.props.workflow.public ? (
            <Trans id='js.Workflows.WorkflowMetadata.visibility.public'>public</Trans>
          ) : (
            <Trans id='js.Workflows.WorkflowMetadata.visibility.private'>private</Trans>
          )}
        </button>
      </li>
    ) : null

    return (
      <ul className='metadata-container'>
        {attribution}
        <li>
          <Trans id='js.Workflows.WorkflowMetadata.update' description="The parameter will contain a time difference (i.e. something like '5h ago')">
            Updated {timeAgo}
          </Trans>
        </li>
        {modalLink}
      </ul>
    )
  }
}
export default withI18n()(WorkflowMetadata)
