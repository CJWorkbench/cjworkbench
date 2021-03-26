import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

const selectAclEntries = (state) => state.workflow.acl
const selectAclLookup = createSelector(selectAclEntries, aclEntries => {
  const lookup = {}
  if (aclEntries) { // skip if there are no entries -- as in unit tests
    aclEntries.forEach(({ email, role }) => { lookup[email] = role })
  }
  return lookup
})

/**
 * Return a mapping from email to role ("viewer", "report-viewer" or "editor").
 *
 * The workflow owner is not included in the mapping.
 */
const selectWorkflowAclLookup = createSelector(
  selectOptimisticState,
  selectAclLookup
)
export default selectWorkflowAclLookup
