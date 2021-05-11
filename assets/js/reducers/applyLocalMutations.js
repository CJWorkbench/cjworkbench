import applyOneMutation from './applyOneMutation'

export default function applyLocalMutations (state) {
  while (state.pendingMutations.length && state.pendingMutations[0].id === null) {
    state = applyOneMutation(state)
  }
  return state
}
