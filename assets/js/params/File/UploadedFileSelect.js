import { PureComponent, useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import {
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter
} from '../../components/Modal'
import filesize from 'filesize'
import { t, Trans } from '@lingui/macro'

const FilesizeOptions = { standard: 'iec', round: 1 }
function formatNBytes (nBytes) {
  return filesize(nBytes, FilesizeOptions)
}

class UploadedFileSelectModal extends PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired, // current uuid
    files: PropTypes.arrayOf(
      PropTypes.shape({
        uuid: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        size: PropTypes.number.isRequired,
        createdAt: PropTypes.string.isRequired
      }).isRequired
    ).isRequired,
    onChange: PropTypes.func.isRequired, // onChoose(uuid) => undefined
    close: PropTypes.func.isRequired // close() => undefined
  }

  state = {
    newValue: this.props.value
  }

  handleClickFile = ev => {
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
        <ModalHeader>
          <Trans
            id='js.params.File.UploadedFileSelect.UploadedFileSelectModal.header.title'
            comment='This should be all-caps for styling reasons'
          >
            FILE HISTORY
          </Trans>
        </ModalHeader>
        <ModalBody>
          {files.length === 0
            ? (
              <p className='no-files'>
                <Trans id='js.params.File.UploadedFileSelect.UploadedFileSelectModal.noFiles'>
                  You have not uploaded any files to this Step
                </Trans>
              </p>
              )
            : (
              <ol className='files'>
                {files.map(({ uuid, size, name, createdAt }) => (
                  <li key={uuid}>
                    <a
                      data-uuid={uuid}
                      href='#'
                      onClick={this.handleClickFile}
                      className={uuid === newValue ? 'selected' : ''}
                    >
                      <div className='name'>{name}</div>
                      <div className='metadata'>
                        <abbr
                          className='size'
                          title={`${numberFormat.format(size)} bytes`}
                        >
                          {formatNBytes(size)}
                        </abbr>
                        <time
                          className='created-at'
                          dateTime={createdAt}
                          title={createdAt}
                        >
                          <Trans
                            id='js.params.File.UploadedFileSelect.UploadedFileSelectModal.uploaded_at'
                            comment='The parameter will contain a specific date'
                          >
                            Uploaded {dateFormat.format(new Date(createdAt))}
                          </Trans>
                        </time>
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
            <Trans id='js.params.File.UploadedFileSelect.UploadedFileSelectModal.footer.loadButton'>
              Load
            </Trans>
          </button>
          <button type='button' name='close' onClick={close}>
            <Trans id='js.params.File.UploadedFileSelect.UploadedFileSelectModal.footer.cancelButton'>
              Cancel
            </Trans>
          </button>
        </ModalFooter>
      </Modal>
    )
  }
}

function SpanOrButton (props) {
  const { className, onClick = undefined, title = undefined, children } = props

  if (onClick !== undefined) {
    return <button className={className} onClick={onClick} title={title}>{children}</button>
  } else {
    return <span className={className}>{children}</span>
  }
}

export default function UploadedFileSelect (props) {
  const { value, files, isReadOnly, onChange } = props
  const [isOpen, setOpen] = useState(false)
  const open = useCallback(() => setOpen(true))
  const close = useCallback(() => setOpen(false))

  if (files.length === 0) return null // no files selected; maybe we're uploading our first

  const valueIndex = files.findIndex(({ uuid }) => uuid === value)
  const canOpen = !isReadOnly && files.findIndex(({ uuid }) => uuid !== value) !== -1 // do not open when nothing to select
  const nFiles = files.length
  const fileNumber = valueIndex + 1

  return (
    <>
      <SpanOrButton
        className='uploaded-file-select'
        onClick={canOpen ? open : undefined}
        title={
          canOpen
            ? t({
                id:
                  'js.params.File.UploadedFileSelect.choosePreviousFile.hoverText',
                message: 'Choose a previously-uploaded file'
              })
            : undefined
        }
      >
        {valueIndex === -1
          ? t({
              id: 'js.params.File.UploadedFileSelect.choosePreviousFile.none',
              comment:
                'Means "No files exist". Very rare; most users will see js.params.File.UploadFileSelect.choosePreviousFile.text first',
              message: 'File [NONE] of {nFiles}',
              values: { nFiles }
            })
          : t({
            id: 'js.params.File.UploadedFileSelect.choosePreviousFile.text',
            comment:
                'The parameter {fileNumber} is the number of the file (or js.params.File.UploadedFileSelect.choosePreviousFile.none) and {nFiles} is the total number of files',
            message: 'File {fileNumber} of {nFiles}',
            values: { fileNumber, nFiles }
          })}
      </SpanOrButton>
      {isOpen
        ? (
          <UploadedFileSelectModal
            value={value}
            files={files}
            onChange={onChange}
            close={close}
          />
          )
        : null}
    </>
  )
}
UploadedFileSelect.propTypes = {
  value: PropTypes.string, // null if no file is selected (also: value might not be in files)
  files: PropTypes.arrayOf(
    PropTypes.shape({
      uuid: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      size: PropTypes.number.isRequired,
      createdAt: PropTypes.string.isRequired
    }).isRequired
  ).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired // func(uuid) => undefined
}
