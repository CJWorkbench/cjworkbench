import React from 'react'
import PropTypes from 'prop-types'

export default function ShareCard ({ workflowId, isPublic }) {
  const [ isModalOpen, setModalOpen ] = React.useState(false)
  const openModal = React.useCallback(() => setModalOpen(true))
  const closeModal = React.useCallback(() => setModalOpen(false))

  return (
    <aside className='share-card'>
      <div className='prompt'>
        <span className='status'>
          {isPublic ? (
            "Anyone can view this report."
          ) : (
            "Only collaborators can view this report."
          )}
        </span>
        <button
          type='button'
          onClick={openModal}
        >Change Workflow sharing</button>
      </div>
      <div className='url'>
        <h4>Report URL</h4>
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
