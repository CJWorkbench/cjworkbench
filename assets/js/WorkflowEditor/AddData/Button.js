/* globals HTMLElement */
import React from 'react'
import ReactDOM from 'react-dom'
import PropTypes from 'prop-types'
import Modal from './Modal'
import { Trans } from '@lingui/macro'

const Button = React.memo(function Button ({ tabSlug, isLessonHighlight, paneRef }) {
  const [isOpen, setOpen] = React.useState(false)
  const open = React.useCallback(() => setOpen(true))
  const close = React.useCallback(() => setOpen(false))
  // When opening a new workflow or switching to a tab, a new Button will
  // appear if there's no data module. Open it automatically!
  //
  // Before mount completes, `paneRef.current === null`; we want
  // `isOpen === false` during mount so we don't try to create a portal at that
  // point. After mount, `paneRef.current` is set and the portal can open.
  // Calling open() at that point invokes a state change, triggering render.
  React.useEffect(open, [])

  return (
    <div className='add-data-button'>
      <button type='button' onClick={open}>
        <i className='icon-add' />{' '}
        <span>
          <Trans id='js.WorkflowEditor.AddData.button' description='This should be all-caps for styling reasons'>ADD DATA</Trans>
        </span>
      </button>
      {isOpen && paneRef.current ? ReactDOM.createPortal((
        <Modal
          tabSlug={tabSlug}
          close={close}
        />
      ), paneRef.current) : null}
    </div>
  )
})
Button.propTypes = {
  tabSlug: PropTypes.string.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  /** <WorkflowEditor/Pane> container, where the dialog will open */
  paneRef: PropTypes.shape({ current: PropTypes.instanceOf(HTMLElement) }).isRequired
}
export default Button
