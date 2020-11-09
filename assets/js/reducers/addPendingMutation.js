export default function addPendingMutation (state, mutation) {
  return {
    ...state,
    pendingMutations: [...(state.pendingMutations || []), mutation]
  }
}
