import React, { lazy, Suspense } from 'react'
import ErrorBoundary from '../../../ErrorBoundary'
const WorkbenchAceEditor = lazy(() => import('./AceEditor'))
import { Trans,t } from '@lingui/macro'
import { withI18n,I18n } from '@lingui/react'

/**
 * AceEditor, loaded dynamically.
 *
 * Include LazyAceEditor instead of AceEditor to move all that JavaScript to a
 * separate file (code splitting).
 */
export default function LazyAceEditor (props) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div className='loading-ace-editor'><Trans id="workflow.loadingeditor">Loading editor...</Trans></div>}>
        <WorkbenchAceEditor {...props} />
      </Suspense>
    </ErrorBoundary>
  )
}
