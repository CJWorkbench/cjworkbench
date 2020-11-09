import applyMutation from '../reducers/applyMutation'

/**
 * Apply all `state.pendingMutations` to the rest of `state`, in order.
 *
 * Any update that throws an error will not be applied. This can happen to
 * Alice in this sort of situation:
 *
 * 1. Alice starts changing Step params -- creating an optimistic update
 * 2. Bob swoops in and deletes the Step
 * 3. We call `selectOptimisticState` before Alice's change has been processed
 */
export default function selectOptimisticState (state) {
  return (state.pendingMutations || []).reduce(applyMutation, state)
}
