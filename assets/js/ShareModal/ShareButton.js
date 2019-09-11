import React from 'react'
import PropTypes from 'prop-types'
import ShareModal from './index'
import { I18n } from '@lingui/react'
import { t } from '@lingui/macro'
/**
 * A <button> that opens/closes a ShareModal.
 *
 * When the user clicks the <button>, the modal opens. The user can close
 * the modal, and then the <button> becomes clickable again.
 */
export default function ShareButton ({ className, children }) {
  const [isOpen, setIsOpen] = React.useState(false)
  const open = React.useCallback(() => setIsOpen(true))
  const close = React.useCallback(() => setIsOpen(false))

  return (
    <>
      <I18n>
        {({ i18n }) => (
          <button
            type='button'
            className='share-button'
            name='share'
            title={i18n._(t('workflow.visibility.sharingTitle')`Change Workflow sharing`)}
            onClick={open}
          >
            {children}
          </button>
        )}

      </I18n>

      {isOpen ? (
        <ShareModal onClickClose={close} />
      ) : null}
    </>
  )
}
ShareButton.propTypes = {
  children: PropTypes.node.isRequired // contents of the button
}
