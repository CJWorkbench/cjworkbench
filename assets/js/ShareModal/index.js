import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import ModalLoader from './ModalLoader'
import { setWorkflowPublicAction } from '../workflow-reducer'

function mapStateToProps (state) {
  const url = `${window.origin}/workflows/${state.workflow.id}`

  return {
    url,
    workflowId: state.workflow.id,
    isPublic: state.workflow.public,
    isReadOnly: !state.workflow.is_owner,
    ownerEmail: state.workflow.owner_email
  }
}

function setIsPublic (isPublic) {
  // Grab workflowId from the state.
  // TODO stop requiring workflowId _anywhere_ in the API/reducer. We should
  // be able to infer it everywhere the way we do in this function.
  return (dispatch, getState) => {
    const workflowId = getState().workflow.id
    return dispatch(setWorkflowPublicAction(workflowId, isPublic))
  }
}

function mapDispatchToProps (dispatch) {
  return {
    onChangeIsPublic: (isPublic) => dispatch(setIsPublic(isPublic))
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ModalLoader)
