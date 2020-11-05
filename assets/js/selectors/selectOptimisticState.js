import applyUpdate from '../reducers/applyUpdate'

function applyOptimisticUpdateIfWeCan (state, update) {
  try {
    return applyUpdate(state, update)
  } catch (err) {
    // TODO make a safer cancel mechanism. Maybe a special kind of Error that
    // is the only kind of Error we catch. Our goal: programming errors should
    // appear in the console as errors, and _expected races_ that we handle
    // correctly should not be logged.
    console.log('Skipping optimistic update because it cannot apply cleanly', update, err)
    return state
  }
}

/**
 * Apply all `state.optimisticUpdates` to the rest of `state`, in order.
 *
 * Any update that throws an error will not be applied. This can happen to
 * Alice in this sort of situation:
 *
 * 1. Alice starts changing Step params -- creating an optimistic update
 * 2. Bob swoops in and deletes the Step
 * 3. We call `selectOptimisticState` before Alice's change has been processed
 */
export default function selectOptimisticState (state) {
  let ret = state
  while (ret.optimisticUpdates && ret.optimisticUpdates.length) {
    ret = applyOptimisticUpdateIfWeCan(ret, ret.optimisticUpdates[0])
  }
  return ret
}
