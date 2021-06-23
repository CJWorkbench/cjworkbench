import { createSelector } from 'reselect'
import selectLoggedInUser from './selectLoggedInUser'

/**
 * Select a boolean indicating whether the logged-in user is paying.
 */
const selectLoggedInUserIsPaying = createSelector(
  selectLoggedInUser,
  u => u.subscribedStripeProductIds.length > 0
)
export default selectLoggedInUserIsPaying
