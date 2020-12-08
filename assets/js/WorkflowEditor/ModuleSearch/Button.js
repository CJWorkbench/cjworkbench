import React from 'react'
import PropTypes from 'prop-types'
import Popup from './Popup'
import { Trans } from '@lingui/macro'

export default function Button (props) {
  const { className, index, tabSlug, isLessonHighlight, isLastAddButton } = props
  const [popperAnchor, setPopperAnchor] = React.useState(null) // HTMLElement set when open
  const handleClickAnchor = React.useCallback(ev => {
    if (popperAnchor) {
      setPopperAnchor(null) // close the menu
    } else {
      setPopperAnchor(ev.currentTarget) // open it
    }
  }, [popperAnchor, setPopperAnchor])
  const handleClose = React.useCallback(ev => setPopperAnchor(null), [setPopperAnchor])

  const buttonClassNames = ['search']
  if (popperAnchor) buttonClassNames.push('active')
  if (isLessonHighlight) buttonClassNames.push('lesson-highlight')

  return (
    <div className={className}>
      <button type='button' className={buttonClassNames.join(' ')} onClick={handleClickAnchor}>
        <i className='icon-add' />{' '}
        <span><Trans id='js.WorkflowEditor.ModuleSearch.Button.addStep' comment='This should be all-caps for styling reasons'>ADD STEP</Trans></span>
      </button>
      {popperAnchor ? (
        <Popup
          isLastAddButton={isLastAddButton}
          index={index}
          tabSlug={tabSlug}
          onClose={handleClose}
          popperAnchor={popperAnchor}
        />
      ) : null}
    </div>
  )
}
Button.propTypes = {
  tabSlug: PropTypes.string.isRequired,
  index: PropTypes.number.isRequired,
  className: PropTypes.string.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  isLastAddButton: PropTypes.bool.isRequired
}
