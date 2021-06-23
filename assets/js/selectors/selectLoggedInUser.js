import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

/**
 * Select the currently logged-in user.
 */
const selectLoggedInUser = createSelector(
  selectOptimisticState,
  state => state.loggedInUser
)
export default selectLoggedInUser
