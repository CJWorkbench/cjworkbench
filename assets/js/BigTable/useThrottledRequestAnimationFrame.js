import React from 'react'

/**
 * Like requestAnimationFrame(), but a flurry of calls is coerced into just the last one.
 *
 * When the `callback` argument changes, the existing queued call is aborted. Use
 * `React.useCallback()` to generate callbacks that only change when you want them
 * to change.
 *
 * Usage:
 *
 *     function MyComponent (props) {
 *       const refresh = React.useCallback(() => console.log('animation frame'))
 *       const throttledRefresh = useThrottledRequestAnimationFrame(callback)
 *
 *       React.useLayoutEffect(() => {
 *         window.addEventListener(window, 'scroll', throttledRefresh)
 *         return () => window.removeEventListener(window, 'scroll', throttledRefresh)
 *       }, [])
 *     }
 *
 * Ref: https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
 */
export default function useThrottledRequestAnimationFrame (callback) {
  // use ref, not state -- state change would force re-render
  const requestId = React.useRef(null)

  const throttledCallback = React.useCallback(time => {
    requestId.current = null
    callback(time)
  }, [callback])

  React.useEffect(() => {
    // Whenever callback changes, cancel existing requests
    return () => {
      if (requestId.current) {
        global.cancelAnimationFrame(requestId.current)
        requestId.current = null
      }
    }
  }, [callback])

  return React.useCallback(function throttledRequestAnimationFrame () {
    if (requestId.current === null) {
      requestId.current = global.requestAnimationFrame(throttledCallback)
    }
  }, [throttledCallback])
}
