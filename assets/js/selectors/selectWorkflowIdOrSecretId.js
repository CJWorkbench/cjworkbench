import { createSelector } from 'reselect'
import selectWorkflowAclLookup from './selectWorkflowAclLookup'

const selectLoggedInUser = (state) => state.loggedInUser
const selectWorkflow = (state) => state.workflow

/**
 * Return the workflow ID or secret ID to use in URLs for network requests.
 *
 * We point clients to the workflow ID whenever that's accessible to them. The
 * fallback is the secret ID.
 */
const selectWorkflowIdOrSecretId = createSelector(
  selectLoggedInUser,
  selectWorkflow,
  selectWorkflowAclLookup,
  (user, workflow, aclLookup) => {
    if (workflow.public || !workflow.secret_id) {
      return workflow.id
    }

    // It has a secret ID. Do we need to use it?
    if (user) {
      if (
        user.email === workflow.owner_email ||
        user.email in aclLookup
      ) {
        return workflow.id
      }
    }

    return workflow.secret_id
  }
)
export default selectWorkflowIdOrSecretId
