// ---- StatusLine ----

// Display error message, if any
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
import React, { useCallback, useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import QuickFix, { QuickFixPropTypes } from './QuickFix'

const StatusLine = React.memo(function StatusLine ({ status, errors, applyQuickFix, isReadOnly }) {
  const [clickedAnyQuickFix, setClickedQuickFix] = useState(false)
  const doApplyQuickFix = useCallback((...args) => {
    setClickedQuickFix(true)
    applyQuickFix(...args)
  })

  // after props change (remember: we're in React.memo), assume the quick fix
  // suggestions are not-yet-clicked.
  useEffect(() => setClickedQuickFix(false), [status, errors])

  if (!errors.length) return null

  return (
    <>
      {errors.map(({ message, quickFixes }, j) => (
        <div className='wf-module-error-msg' key={j}>
          <p>{message}</p>
          {quickFixes && quickFixes.length && !isReadOnly ? (
            <ul className='quick-fixes'>
              {quickFixes.map((quickFix, i) => (
                <li key={i}>
                  <QuickFix
                    disabled={clickedAnyQuickFix}
                    applyQuickFix={doApplyQuickFix}
                    {...quickFix}
                  />
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </>
  )
})
StatusLine.propTypes = {
  status: PropTypes.oneOf(['ok', 'busy', 'error', 'unreachable']).isRequired,
  isReadOnly: PropTypes.bool.isRequired, // if true, cannot apply quick fixes
  errors: PropTypes.arrayOf(PropTypes.shape({ message: PropTypes.string.isRequired, quickFixes: PropTypes.arrayOf(PropTypes.shape(QuickFixPropTypes)) })), // may be empty
  applyQuickFix: PropTypes.func.isRequired // func(action, args) => undefined
}

export default StatusLine
