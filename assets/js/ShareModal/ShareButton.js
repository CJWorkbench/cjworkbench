import React from 'react'
import PropTypes from 'prop-types'
import ShareModal from './index'

/**
 * A <button> that opens/closes a ShareModal.
 *
 * When the user clicks the <button>, the modal opens. The user can close
 * the modal, and then the <button> becomes clickable again.
 */
export default function ShareButton ({ className, children }) {
  const [ isOpen, setIsOpen ] = React.useState(false)
  const open = React.useCallback(() => setIsOpen(true))
  const close = React.useCallback(() => setIsOpen(false))

  return (
    <>
      <button
        type='button'
        className='share-button'
        name='share'
        title='Change Workflow sharing'
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
