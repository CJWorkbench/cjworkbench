import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import ShareUrl from './components/ShareUrl'
import { Modal, ModalHeader, ModalBody, ModalFooter } from './components/Modal'
import { Trans } from '@lingui/macro'

export default class ExportModal extends PureComponent {
  static propTypes = {
    open: PropTypes.bool.isRequired,
    stepId: PropTypes.number.isRequired, // to build download URLs
    toggle: PropTypes.func.isRequired
  }

  buildUrlString (ext) {
    const path = `/public/moduledata/live/${this.props.stepId}.${ext}`
    if (window.location.href === 'about:blank') {
      // allowing an out for testing (there is no window.location.href during test)
      return path
    } else {
      return new URL(path, window.location.href).href
    }
  }

  get csvUrlString () {
    return this.buildUrlString('csv')
  }

  get jsonUrlString () {
    return this.buildUrlString('json')
  }

  handleClickClose = () => this.props.toggle()

  render () {
    return (
      <Modal
        isOpen={this.props.open}
        className='export'
        toggle={this.props.toggle}
      >
        <ModalHeader>
          <Trans
            id='js.ExportModal.header.title'
            comment='This should be all-caps for styling reasons'
          >
            EXPORT DATA
          </Trans>
        </ModalHeader>
        <ModalBody>
          <dl>
            <dt>
              <Trans
                id='js.ExportModal.type.CSV'
                comment='"CSV" (all-caps) is a kind of file'
              >
                CSV
              </Trans>
            </dt>
            <dd>
              <ShareUrl url={this.csvUrlString} download />
            </dd>
            <dt>
              <Trans
                id='js.ExportModal.type.JSON'
                comment='"JSON" (all-caps) is a kind of file'
              >
                JSON
              </Trans>
            </dt>
            <dd>
              <ShareUrl url={this.jsonUrlString} download />
            </dd>
          </dl>
        </ModalBody>
        <ModalFooter>
          <button
            type='button'
            onClick={this.handleClickClose}
            className='button-blue action-button test-done-button'
          >
            <Trans
              id='js.ExportModal.footer.doneButton'
              comment='Acts as closing button'
            >
              Done
            </Trans>
          </button>
        </ModalFooter>
      </Modal>
    )
  }
}
