import applyOneMutation from './applyOneMutation'

export default function applyMutations (state) {
  while (state.pendingMutations.length) {
    state = applyOneMutation(state)
  }
  return state
}
