import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

function reindex (steps) {
  const bySlug = {}
  Object.values(steps).forEach(step => { bySlug[step.slug] = step })
  return bySlug
}

/**
 * Select a mapping from Step slug => Step.
 */
const selectStepsBySlug = createSelector(selectOptimisticState, state => reindex(state.steps))
export default selectStepsBySlug
