import { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import ShareModal from './index'
import { t } from '@lingui/macro'

/**
 * A <button> that opens/closes a ShareModal.
 *
 * When the user clicks the <button>, the modal opens. The user can close
 * the modal, and then the <button> becomes clickable again.
 */
export default function ShareButton ({ className, children }) {
  const [isOpen, setIsOpen] = useState(false)
  const open = useCallback(() => setIsOpen(true))
  const close = useCallback(() => setIsOpen(false))

  return (
    <>
      <button
        type='button'
        className='share-button'
        name='share'
        title={t({ id: 'js.ShareModal.ShareButton.button.hoverText', message: 'Change Workflow sharing' })}
        onClick={open}
      >
        {children}
      </button>

      {isOpen ? (
        <ShareModal onClickClose={close} />
      ) : null}
    </>
  )
}
ShareButton.propTypes = {
  children: PropTypes.node.isRequired // contents of the button
}
