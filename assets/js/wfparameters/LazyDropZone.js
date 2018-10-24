import React, { lazy, Suspense } from 'react'
const DropZone = lazy(() => import('./DropZone'))

/**
 * DropZone, loaded dynamically.
 *
 * Include LazyDropZone instead of DropZone to move all that JavaScript to a
 * separate file (code splitting).
 */
export default function LazyDropZone(props) {
  return (
    <Suspense fallback={<div className='loading-drop-zone'>Loading uploader...</div>}>
      <DropZone {...props} />
    </Suspense>
  )
}
