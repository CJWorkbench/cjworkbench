import { useRef } from 'react'

function isArrayEqual (lhs, rhs) {
  return lhs.length === rhs.length && lhs.every((v, i) => v === rhs[i])
}

function areDepsEqualWithArrayCompare (lhs, rhs) {
  return lhs.every((v, i) => Array.isArray(v) ? isArrayEqual(v, rhs[i]) : Object.is(v, rhs[i]))
}

/**
 * Like React.useCallback() ... but Array dependencies are compared deeply for one level.
 */
export default function useCallbackWithArrayComparedDeps (callback, deps) {
  const last = useRef(null)

  if (last.current === null || !areDepsEqualWithArrayCompare(last.current.deps, deps)) {
    last.current = { deps, callback }
  }

  return last.current.callback
}
