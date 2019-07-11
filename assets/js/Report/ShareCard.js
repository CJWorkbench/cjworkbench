import React from 'react'
import PropTypes from 'prop-types'
import ShareButton from '../ShareModal/ShareButton'

export default function ShareCard ({ workflowId, isPublic }) {
  return (
    <aside className='share-card'>
      <div className='prompt'>
        <span className='status'>
          {isPublic ? (
            'This workflow is public'
          ) : (
            'This workflow is private'
          )}
        </span>
        <ShareButton>Edit Privacy</ShareButton>
      </div>
      <div className='url'>
        <h4>Report URL</h4>
        <p className='accessible-to'>
          {isPublic ? (
            'Anyone can view this report'
          ) : (
            'Only collaborators can view this report'
          )}
        </p>
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
