import React from 'react'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../components/Modal'
import filesize from 'filesize'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const FilesizeOptions = { standard: 'iec', round: 1 }
function formatNBytes (nBytes) {
  return filesize(nBytes, FilesizeOptions)
}

class UploadedFileSelectModal extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired, // current uuid
    files: PropTypes.arrayOf(PropTypes.shape({
      uuid: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      size: PropTypes.number.isRequired,
      createdAt: PropTypes.string.isRequired
    }).isRequired).isRequired,
    onChange: PropTypes.func.isRequired, // onChoose(uuid) => undefined
    close: PropTypes.func.isRequired // close() => undefined
  }

  state = {
    newValue: this.props.value
  }

  handleClickFile = (ev) => {
    const uuid = ev.currentTarget.getAttribute('data-uuid')
    this.setState({ newValue: uuid })
  }

  handleClickSelect = () => {
    const { onChange, value, close } = this.props
    const { newValue } = this.state
    if (newValue !== value) onChange(newValue)
    close()
  }

  render () {
    const { value, files, close } = this.props
    const { newValue } = this.state
    const numberFormat = new Intl.NumberFormat()
    const dateFormat = new Intl.DateTimeFormat('default', {
      weekday: 'long',
      hour: 'numeric',
      minute: 'numeric',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    })

    return (
      <Modal className='uploaded-file-select-modal' isOpen toggle={close}>
        <ModalHeader>FILE HISTORY</ModalHeader>
        <ModalBody>
          {files.length === 0 ? (
            <p className='no-files'>You have not uploaded any files to this Step</p>
          ) : (
            <ol className='files'>
              {files.map(({ uuid, size, name, createdAt }) => (
                <li key={uuid}>
                  <a data-uuid={uuid} href='#' onClick={this.handleClickFile} className={uuid === newValue ? 'selected' : ''}>
                    <div className='name'>{name}</div>
                    <div className='metadata'>
                      <abbr className='size' title={`${numberFormat.format(size)} bytes`}>
                        {formatNBytes(size)}
                      </abbr>
                      <time className='created-at' dateTime={createdAt} title={createdAt}>Uploaded {dateFormat.format(new Date(createdAt))}</time>
                    </div>
                  </a>
                </li>
              ))}
            </ol>
          )}
        </ModalBody>
        <ModalFooter>
          <button
            type='button'
            name='select'
            onClick={this.handleClickSelect}
            disabled={newValue === value}
          >
            Load
          </button>
          <button
            type='button'
            name='close'
            onClick={close}
          >
            Cancel
          </button>
        </ModalFooter>
      </Modal>
    )
  }
}

const UploadedFileSelect = React.memo(function UploadedFileSelect ({ value, files, onChange }) {
  const [isOpen, setOpen] = React.useState(false)
  const open = React.useCallback(() => setOpen(true))
  const close = React.useCallback(() => setOpen(false))

  if (files.length === 0) return null // no files selected; maybe we're uploading our first

  const valueIndex = files.findIndex(({ uuid }) => uuid === value)
  const canOpen = files.findIndex(({ uuid }) => uuid !== value) !== -1 // do not open when nothing to select

  return (
    <>
      <button className='uploaded-file-select' onClick={open} title={canOpen ? this.props._(t('js.params.File.UploadedFileSelect.choosePreviousFile.button')`Choose a previously-uploaded file`) : undefined} disabled={!canOpen}>
        {`File ${valueIndex === -1 ? '[NONE]' : (valueIndex + 1)} of ${files.length}`}
      </button>
      {isOpen ? (
        <UploadedFileSelectModal
          value={value}
          files={files}
          onChange={onChange}
          close={close}
        />
      ) : null}
    </>
  )
})
UploadedFileSelect.propTypes = {
  value: PropTypes.string, // null if no file is selected (also: value might not be in files)
  files: PropTypes.arrayOf(PropTypes.shape({
    uuid: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    size: PropTypes.number.isRequired,
    createdAt: PropTypes.string.isRequired
  }).isRequired).isRequired,
  onChange: PropTypes.func.isRequired // func(uuid) => undefined
}
export default withI18n()(UploadedFileSelect)
