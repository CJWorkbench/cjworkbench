import React from 'react'

function buildDataUrl ({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId }) {
  return (moduleSlug === null || deltaId === null)
    ? null
    : `${window.origin}/workflows/${workflowIdOrSecretId}/steps/${stepSlug}/delta-${deltaId}/result-json.json`
}

function buildSrc ({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, wantOrigin }) {
  if (moduleSlug === null) {
    return null
  }
  const dataUrl = buildDataUrl({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId })
  const origin = new URL(window.location).origin
  const moduleUrl = `${origin}/modules/${moduleSlug}.html`
  return wantOrigin
    ? `${moduleUrl}?dataUrl=${encodeURIComponent(dataUrl || '')}&origin=${origin}`
    : `${moduleUrl}?dataUrl=${encodeURIComponent(dataUrl || '')}`
}

export function useChartIframeSrc ({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId }) {
  return buildSrc({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, wantOrigin: false })
}

/**
 * Return a "cached" `src` and ensure `iframeRef` receives `dataUrl`.
 *
 * It's complicated:
 *
 * * When `deltaId` is null, `dataUrl` is null.
 * * When called with a new `moduleSlug`, `workflowIdOrSecretId`, `stepSlug` or
 *   `deltaId`, we build a new `src` with the `dataUrl` embedded.
 * * When called with a new `iframeEl`, we attach an event listener, waiting
 *   for a `subscribe-to-data-url` event.
 * * Before `subscribe-to-data-url`, we generate a new `src` every time new
 *   params are called.
 * * After `subscribe-to-data-url`, we "lock" the `src` so it remains constant
 *   even as `deltaId` changes; we send `dataUrl` to `iframeEl` via
 *   `window.postMessage()` instead.
 *
 * Special case: if `moduleSlug` is null, return null.
 */
export function useChartIframeSrcWithDataUrlSubscription ({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, iframeEl }) {
  const lockedSrcRef = React.useRef(null) // { key: key, src: ... }
  const srcKey = [moduleSlug || '', workflowIdOrSecretId, stepSlug || ''].join('|')

  const dataUrl = buildDataUrl({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId })
  let src
  if (lockedSrcRef.current && lockedSrcRef.current.key === srcKey) {
    src = lockedSrcRef.current.src
  } else {
    lockedSrcRef.current = null // in case we moved to a new `moduleSlug`
    src = buildSrc({ workflowIdOrSecretId, moduleSlug, stepSlug, deltaId, wantOrigin: true })
  }

  const handleMessage = React.useCallback(ev => {
    if (!src || !iframeEl || ev.source !== iframeEl.contentWindow) {
      return // the message isn't from the iframe
    }

    if (ev.origin !== new URL(src).origin) {
      return // the user navigated _within_ the iframe to a new domain
    }

    if (iframeEl.src !== src) {
      return // we're handling this old message after navigating to a new URL
    }

    const data = ev.data
    if (data.type === 'subscribe-to-data-url') {
      lockedSrcRef.current = iframeEl.src
    }
  }, [iframeEl, lockedSrcRef, src])

  // Install message handler, to handle messages from iframe.
  // When we change src, the old handler is removed and a new one is added.
  React.useEffect(() => {
    if (iframeEl) {
      window.addEventListener('message', handleMessage)
      return () => window.removeEventListener('message', handleMessage)
    }
  }, [iframeEl, handleMessage])

  // Send a message to the iframe on every render, once we're locked
  React.useEffect(() => {
    if (!iframeEl || lockedSrcRef.current === null) {
      return
    }

    iframeEl.contentWindow.postMessage(
      { type: 'set-data-url', dataUrl: dataUrl || '' },
      new URL(lockedSrcRef.current.src).origin
    )
  }, [iframeEl, lockedSrcRef.current, dataUrl])

  return src
}
