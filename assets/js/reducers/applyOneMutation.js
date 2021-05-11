import mutations from '../mutations'

export default function applyOneMutation (state) {
  const { type, args } = state.pendingMutations[0]
  if (!(type in mutations)) {
    throw new Error('Invalid mutation type ' + type)
  }
  const reducer = mutations[type]
  return {
    ...reducer(state, args),
    pendingMutations: state.pendingMutations.slice(1)
  }
}
