// ---- StatusLine ----

// Display error message, if any
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
import React, { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import QuickFix, { QuickFixPropTypes } from './QuickFix'


const StatusLine = React.memo(function StatusLine ({ status, error, quickFixes, applyQuickFix }) {
  const [clickedAnyQuickFix, setClickedQuickFix] = useState(false)
  const doApplyQuickFix = useCallback((...args) => {
    setClickedQuickFix(true)
    applyQuickFix(...args)
  })

  // after props change (remember: we're in React.memo), assume the quick fix
  // suggestions are not-yet-clicked.
  useEffect(() => setClickedQuickFix(false))

  if (!error && !quickFixes.length) return null

  return (
    <div className='wf-module-error-msg'>
      {error ? (
        <p>{error}</p>
      ) : null}
      {quickFixes.length ? (
        <ul className='quick-fixes'>
          {quickFixes.map((quickFix, i) => (
            <QuickFix
              key={i}
              disabled={clickedAnyQuickFix}
              applyQuickFix={doApplyQuickFix}
              {...quickFix}
            />
          ))}
        </ul>
      ) : null}
    </div>
  )
})
StatusLine.propTypes = {
  status: PropTypes.oneOf(['ok', 'busy', 'error', 'unreachable']).isRequired,
  error: PropTypes.string, // may be empty string
  quickFixes: PropTypes.arrayOf(PropTypes.shape(QuickFixPropTypes).isRequired).isRequired,
  applyQuickFix: PropTypes.func.isRequired, // func(action, args) => undefined
}

export default StatusLine
