import { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { supportedLocalesData, currentLocaleId } from './locales'
import { csrfToken } from '../utils'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'

/**
 * A menu for the user to select a locale.
 */
export default function LocaleSwitcher ({ closeModal }) {
  const [newLocaleId, setNewLocaleId] = useState(null) // null, "en", "fr", etc., ..., true if we don't know
  const handleSubmit = useCallback(ev => {
    if (newLocaleId !== null) {
      // we're already submitting. Ignore.
      ev.preventDefault()
      ev.stopPropagation()
    } else {
      // Grab new locale ID from the <button> we clicked.
      // (This isn't defensively programmed. It can probably set
      // newLocaleId to just about anything truthy. That's okay.)
      setNewLocaleId(
        (document.activeElement && document.activeElement.value) || true
      )
      // and continue submitting
    }
  })

  return (
    <Modal isOpen className='locale-switcher' toggle={closeModal}>
      <ModalHeader toggle={closeModal}>
        <Trans
          id='js.i18n.LocaleSwitcher.header.title'
          comment='This should be all-caps for styling reasons'
        >
          LANGUAGE
        </Trans>
      </ModalHeader>
      <ModalBody>
        <p className='description'>
          <Trans id='js.i18n.LocaleSwitcher.body.description'>
            Choose the language of Workbench’s interface. Data is not affected.
          </Trans>
        </p>
        <form method='POST' action='/locale' onSubmit={handleSubmit}>
          <input type='hidden' name='next' value={window.location.href} />
          <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
          <fieldset>
            {supportedLocalesData.map(({ id, name }) => (
              <button
                key={id}
                className={id === newLocaleId ? 'submitting' : undefined}
                disabled={id === currentLocaleId}
                type='submit'
                name='new_locale'
                value={id}
              >
                {name}
              </button>
            ))}
          </fieldset>
        </form>
      </ModalBody>
      <ModalFooter>
        <button className='action-button button-gray' onClick={closeModal}>
          <Trans
            id='js.i18n.LocaleSwitcher.footer.close'
            comment='Close the dialog box'
          >
            Close
          </Trans>
        </button>
      </ModalFooter>
    </Modal>
  )
}

LocaleSwitcher.propTypes = {
  closeModal: PropTypes.func.isRequired
}
