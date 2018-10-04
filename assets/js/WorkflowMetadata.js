// WorkflowMetadata: that line below the workflow title
// which shows owner, last modified date, public/private

import React from 'react'
import PropTypes from 'prop-types'
import { timeDifference } from './utils'

export default class WorkflowMetadata extends React.Component {
  static propTypes = {
    workflow: PropTypes.object.isRequired,
    openShareModal: PropTypes.func.isRequired, // func() => undefined
    test_now: PropTypes.object  // optional injection for testing, avoid time zone issues for Last Update time
  }

  render () {
    const now = this.props.test_now || new Date()

    // don't show author if this workflow is anonymous
    const attribution = !this.props.workflow.is_anonymous ? (
      <li className="attribution">
        <span className="metadata">by {this.props.workflow.owner_name.trim()}</span>
        <span className="separator">-</span>
      </li>
    ) : null

    const modalLink = !(this.props.workflow.read_only || this.props.workflow.is_anonymous) ? (
      <li>
        <span className='separator'>-</span>
        <button className="public-private" title="Change privacy" onClick={this.props.openShareModal}>
          {this.props.workflow.public ? 'public' : 'private'}
        </button>
      </li>
    ) : null

    return (
      <ul className="metadata-container">
        {attribution}
        <li>
          Updated {timeDifference(this.props.workflow.last_update, now)}
        </li>
        {modalLink}
      </ul>
    )
  }
}
