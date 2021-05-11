import applyMutations from '../reducers/applyMutations'

/**
 * Apply all `state.pendingMutations` to the rest of `state`, in order.
 *
 * Mutations that cannot apply will be no-ops. This can happen to Alice
 * in this sort of situation:
 *
 * 1. Alice starts changing Step params -- creating an optimistic update
 * 2. Bob swoops in and deletes the Step
 * 3. We call `selectOptimisticState` before Alice's change has been processed
 */
export default function selectOptimisticState (state) {
  if ('pendingMutations' in state) {
    return applyMutations(state)
  } else {
    return state
  }
}
