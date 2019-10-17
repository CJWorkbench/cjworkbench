// WorkflowMetadata: that line below the workflow title
// which shows owner, last modified date, public/private

import React from 'react'
import PropTypes from 'prop-types'
import { timeDifference } from '../utils'
import { withI18n,I18n } from '@lingui/react'
import { Trans,t } from '@lingui/macro'

export default withI18n()(class WorkflowMetadata extends React.Component {
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

    // don't show author if this workflow is anonymous
    const attribution = !this.props.workflow.is_anonymous ? (
      <li className='attribution'>
        <span className='metadata'>by {this.props.workflow.owner_name.trim()}</span>
        <span className='separator'>-</span>
      </li>
    ) : null

    const modalLink = !(this.props.workflow.read_only || this.props.workflow.is_anonymous) ? (
      <li>
        <span className='separator'>-</span>
        
        <button type='button' className='public-private' title={this.props.i18n._(t('workflow.visibility.changeprivacy')`Change privacy`)} onClick={this.handleClickOpenShareModal}>
          {this.props.workflow.public ? this.props.i18n._(t('workflow.public')`public`) : this.props.i18n._(t('workflow.private')`private`)}
        </button> 
      </li>
    ) : null

    return (
      <ul className='metadata-container'>
        {attribution}
        <li>
          <Trans id="workflow.updated">Updated</Trans> {timeDifference(this.props.workflow.last_update, now, this.props.i18n)}
        </li>
        {modalLink}
      </ul>
    )
  }
})
