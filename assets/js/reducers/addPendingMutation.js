/**
 * Predict that the server will send a mutation (or cancellation).
 *
 * Add to `state.pendingMutations`; we'll remove from it when the server
 * responds for `mutation.id`.
 */
export default function addPendingMutation (state, mutation) {
  return {
    ...state,
    pendingMutations: [...(state.pendingMutations || []), mutation]
  }
}
