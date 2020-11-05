export default function addOptimisticUpdate (state, optimisticUpdate) {
  return {
    ...state,
    optimisticUpdates: [...(state.optimisticUpdates || []), optimisticUpdate]
  }
}
