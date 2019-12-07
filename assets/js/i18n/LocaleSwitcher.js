import * as React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { supportedLocalesData, currentLocale } from './locales'
import { csrfToken } from '../utils'
import { Modal, ModalHeader, ModalBody } from '../components/Modal'

/**
 * Decides whether to enable locale switching.
 *
 * Uses window.i18nConfig, which is injected by Django in the base template
 */
export const enableLocaleSwitcher = window.i18nConfig && window.i18nConfig.showSwitcher

/**
 * A menu for the user to select a locale.
 */
export default class LocaleSwitcher extends React.PureComponent {
  handleLocaleChange (ev) {
    ev.target.form.submit()
  }

  render () {
    return (
      <Modal isOpen toggle={this.props.closeModal}>
        <ModalHeader toggle={this.props.closeModal}>
          <Trans id='js.i18n.LocaleSwitcher.header.title' description='This should be all-caps for styling reasons'>
            LANGUAGES
          </Trans>
        </ModalHeader>
        <ModalBody>
          <p>
            <Trans id='js.i18n.LocaleSwitcher.body.description'>
              This option will change the language of Workbench's interface. To submit translations for your language, visit <a href='#'>this</a> page.
            </Trans>
          </p>
          <form method='POST' action='/locale'>
            <input type='hidden' name='next' value={window.location.href} />
            <input type='hidden' name='csrfmiddlewaretoken' value={csrfToken} />
            {supportedLocalesData.map((localeData) => (
              <label key={localeData.locale_id}>
                <input
                  type='radio'
                  name='new_locale'
                  value={localeData.locale_id}
                  checked={localeData.locale_id === currentLocale}
                  onChange={this.handleLocaleChange}
                />
                {localeData.locale_name}
              </label>
            ))}
          </form>
        </ModalBody>
      </Modal>
    )
  }
}

LocaleSwitcher.propTypes = {
  closeModal: PropTypes.func.isRequired
}
