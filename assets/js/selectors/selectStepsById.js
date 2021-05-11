import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

/**
 * Select a mapping from Step ID => Step.
 *
 * TODO nix step IDs from client side entirely and use slugs instead.
 */
const selectStepsById = createSelector(selectOptimisticState, state => state.steps)
export default selectStepsById
