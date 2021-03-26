import { createSelector } from 'reselect'
import selectLoggedInUserRole from './selectLoggedInUserRole'

/**
 * Select whether the logged-in (or anonymous) user may modify the workflow.
 *
 * (This has no security implications. Callers use it to _hide_ buttons and
 * fields that wouldn't work even if they weren't hidden.)
 */
const selectIsReadOnly = createSelector(
  selectLoggedInUserRole,
  role => role !== 'owner' && role !== 'editor'
)
export default selectIsReadOnly
