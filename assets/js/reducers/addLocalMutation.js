import mutations from '../mutations'

/**
 * Schedule (or apply) mutation after `pendingMutations` are all run.
 *
 * The canonical example is "select tab". This can only happen after we create
 * the tab. So imagine this example sequence:
 *
 * 1. create tab "A" (pending mutation -- the server must respond)
 * 2. select tab "A" (local mutation -- no server needed, but it depends on 1)
 * 3. delete tab "A" (pending mutation)
 *
 * In this example, 2 must be resolved after 1.
 *
 * When mutations are pending, we mark local mutations in the state by setting
 * their ID to null. All local mutations are resolved (or ignored, if they don't
 * succeed) after the server resolves all prior pending mutations.
 *
 * When mutations are _not_ pending, `addLocalMutation()` applies the mutation
 * immediately.
 */
export default function addLocalMutation (state, mutation) {
  if (mutation.id !== null) {
    throw new Error('mutation.id must be null')
  }
  if (!('pendingMutations' in state) || state.pendingMutations.length === 0) {
    const { type, args } = mutation
    if (!(type in mutations)) {
      throw new Error('Invalid mutation type ' + type)
    }
    const reducer = mutations[type]
    return reducer(state, args)
  } else {
    return {
      ...state,
      pendingMutations: [...state.pendingMutations, mutation]
    }
  }
}
