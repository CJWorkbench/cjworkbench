export default function removePendingMutation (state, id) {
  if ((state.pendingMutations || []).some(m => m.id === id)) {
    return {
      ...state,
      pendingMutations: state.pendingMutations.filter(m => m.id !== id)
    }
  } else {
    return state // same identity as input -- helps with memoize
  }
}
