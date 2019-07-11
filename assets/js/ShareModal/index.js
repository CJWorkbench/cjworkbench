import { connect } from 'react-redux'
import { logUserEvent } from '../utils'
import * as actions from './actions'
import Modal from './Modal'

function logShare (type) {
  logUserEvent('Share workflow ' + type)
}

function mapStateToProps (state) {
  const url = `${window.origin}/workflows/${state.workflow.id}`

  return {
    url,
    acl: state.workflow.acl,
    workflowId: state.workflow.id,
    isPublic: state.workflow.public,
    isReadOnly: !state.workflow.is_owner,
    ownerEmail: state.workflow.owner_email,
    logShare
  }
}

const mapDispatchToProps = {
  setIsPublic: actions.setWorkflowPublicAction,
  updateAclEntry: actions.updateAclEntryAction,
  deleteAclEntry: actions.deleteAclEntryAction
}

export default connect(mapStateToProps, mapDispatchToProps)(Modal)
