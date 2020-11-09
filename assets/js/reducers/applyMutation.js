import mutations from '../mutations'
import removePendingMutation from './removePendingMutation'

export default function applyMutation (state, mutation) {
  const { id, type, args } = mutation
  if (!(type in mutations)) {
    throw new Error('Invalid mutation type ' + type)
  }
  const reducer = mutations[type]
  return removePendingMutation(reducer(state, args), id)
}
