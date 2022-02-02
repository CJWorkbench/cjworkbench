import { connect } from 'react-redux'
import * as actions from './actions'
import Modal from './Modal'
import selectLoggedInUserRole from '../selectors/selectLoggedInUserRole'

function mapStateToProps (state) {
  const { loggedInUser, workflow } = state

  return {
    acl: workflow.acl,
    workflowId: workflow.id,
    isPublic: workflow.public,
    secretId: workflow.secret_id,
    isReadOnly: selectLoggedInUserRole(state) !== 'owner',
    ownerEmail: workflow.owner_email,
    canCreateSecretLink: loggedInUser.limits.can_create_secret_link,
  }
}

const mapDispatchToProps = {
  setWorkflowPublicAccess: actions.setWorkflowPublicAccessAction,
  updateAclEntry: actions.updateAclEntryAction,
  deleteAclEntry: actions.deleteAclEntryAction
}

export default connect(mapStateToProps, mapDispatchToProps)(Modal)
