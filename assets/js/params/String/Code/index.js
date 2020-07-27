import React, { lazy, Suspense } from 'react'
import ErrorBoundary from '../../../ErrorBoundary'
import { Trans } from '@lingui/macro'

const WorkbenchAceEditor = lazy(() => import('./AceEditor'))

/**
 * AceEditor, loaded dynamically.
 *
 * Include LazyAceEditor instead of AceEditor to move all that JavaScript to a
 * separate file (code splitting).
 */
export default function LazyAceEditor (props) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div className='loading-ace-editor'><Trans id='js.params.Custom.code.loadingEditor'>Loading editor...</Trans></div>}>
        <WorkbenchAceEditor {...props} />
      </Suspense>
    </ErrorBoundary>
  )
}
