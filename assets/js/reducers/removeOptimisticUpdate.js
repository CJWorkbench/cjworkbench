export default function removeOptimisticUpdate (state, id) {
  const notMatch = (optimisticUpdate) => optimisticUpdate.optimisticId === id
  if ((state.optimisticUpdates || []).every(notMatch)) {
    return state // same as input -- helps with memoize
  } else {
    return {
      ...state,
      optimisticUpdates: state.optimisticUpdates.filter(notMatch)
    }
  }
}
