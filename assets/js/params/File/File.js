import React from 'react'
import PropTypes from 'prop-types'
import UploadedFileSelect from './UploadedFileSelect'

const UploadProgress = React.memo(function UploadProgress ({ nBytesTotal, nBytesUploaded }) {
  const percent = (nBytesUploaded || 0) / nBytesTotal * 100
  const title = nBytesUploaded === null ? '' : `${percent.toFixed(1) + '% uploaded'}`
  return (
    <div className='upload-progress' title={title}>
      <div className='value' style={{ width: `${percent}%` }} />
    </div>
  )
})

/**
 * A file-upload field.
 *
 * A file-upload field actually maintains a _list_ of file uploads, even
 * though the user only sees one at a time. (This is cruft: we used to
 * support "Versions" of files, it's expensive to _remove_ that feature now,
 * even though it's rarely used.) The `value` is a UUID; the `files` prop
 * is a list of UploadedFiles that must include `value`.
 *
 * Features:
 *
 * User can change `value` by opening a Modal that shows all `files`.
 * User can change `value` by uploading a new file.
 * After changing `value`, we auto-submit our new params.
 * Prompts user when `value` is not in `files`.
 */
export default class File extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(n) => undefined
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    name: PropTypes.string.isRequired, // <input name=...>
    files: PropTypes.arrayOf(PropTypes.shape({
      uuid: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      size: PropTypes.number.isRequired,
      createdAt: PropTypes.string.isRequired // ISO8601-formatted date
    }).isRequired).isRequired,
    wfModuleId: PropTypes.number.isRequired,
    inProgressUpload: PropTypes.shape({
      name: PropTypes.string.isRequired,
      size: PropTypes.number.isRequired,
      nBytesUploaded: PropTypes.number // or null when waiting for start/cancel
    }), // or null/undefined
    fieldId: PropTypes.string.isRequired,
    value: PropTypes.string, // String-encoded UUID or null
    upstreamValue: PropTypes.string, // String-encoded UUID or null
    uploadFile: PropTypes.func.isRequired, // func(wfModuleId, file) => Promise(<{uuid: ...}, or null if aborted>)
    cancelUpload: PropTypes.func.isRequired // func(wfModuleId) => undefined
  }

  _upload = (file) => {
    const { name, uploadFile, setWfModuleParams, wfModuleId } = this.props
    uploadFile(wfModuleId, file)
      .then(result => {
        // The upload completed; now change the param server-side. That way
        // the user won't need to click the Go button after upload.
        //
        // Assumes ChangeParametersCommand allows partial params.
        if (result.value && result.value.uuid) { // ignore abort, which wouldn't set value/uuid
          setWfModuleParams(wfModuleId, { [name]: result.value.uuid })
        }
      })
  }

  onDragOver = (ev) => {
    const items = ev.dataTransfer.items
    if (items && items.length === 1 && items[0].kind === 'file') {
      // allow dropping
      ev.preventDefault()
      ev.stopPropagation()
      ev.dataTransfer.dropEffect = 'copy'
    }
  }

  onDragEnter = (ev) => {
    // DO NOT use `this.state`!
    //
    // https://stackoverflow.com/questions/7110353/html5-dragleave-fired-when-hovering-a-child-element
    //
    // dragenter and dragleave bubble up from children; and they _fire_ on
    // children. The only reliable way to stop them from bubbling is to set
    // `pointer-events: none;`.
    //
    // ... but we _can't_ set `pointer-events: none;` because we have a
    // <input type=file> in there.
    //
    // The solution: set `pointer-events; none` _immediately_ when the user
    // drags over the element. We can't use `this.setState()` because that has
    // no effect until the next render() -- by which point it's too late because
    // other events might happen that break things.
    ev.currentTarget.classList.add('dragging-over')
  }

  onDragLeave = (ev) => {
    if (
      ev.currentTarget.classList.contains('dragging-over') &&
      ev.target !== ev.currentTarget
    ) {
      // We got a drag-leave event on a _child_ element. That ought to be
      // impossible because we set pointer-events:none on children. But it can
      // happen right at the very beginning of drag-over.
      //
      // Ignore this event.
      //
      // This test can find false positives; hopefully it, er, won't. It isn't
      // the end of the world if the user moves away and the text is still
      // "drop here" -- because if the user dragged a file over the page the
      // user probably _means_ to drop here but flubbed a mouse operation.
      return
    }
    ev.currentTarget.classList.remove('dragging-over')
  }

  onDrop = (ev) => {
    const file = ev.dataTransfer.files[0]
    ev.preventDefault() // don't open the file with the web browser
    ev.stopPropagation() // don't open the file with the web browser
    this._upload(file)
    ev.currentTarget.classList.remove('dragging-over')
  }

  onChange = (value) => {
    const { setWfModuleParams, wfModuleId, name } = this.props
    setWfModuleParams(wfModuleId, { [name]: value })
  }

  onChangeFileInput = (ev) => {
    const file = ev.target.files[0]
    this._upload(file)
  }

  cancelUpload = () => {
    const { wfModuleId, cancelUpload } = this.props
    cancelUpload(wfModuleId)
  }

  render () {
    const { name, value, files, inProgressUpload, fieldId, isReadOnly } = this.props
    const file = files.find(f => f.uuid === value)

    return (
      <div
        className='drop-zone'
        onDrop={this.onDrop}
        onDragOver={this.onDragOver}
        onDragEnter={this.onDragEnter}
        onDragLeave={this.onDragLeave}
      >
        {inProgressUpload ? (
          <div className='uploading-file'>
            <div className='filename'>{inProgressUpload.name}</div>
            <div className='status'>
              <UploadedFileSelect isReadOnly value={value} files={files} onChange={this.onChange} />
              <button type='button' onClick={this.cancelUpload} name='cancel-upload' title='Cancel upload'>
                Cancel Upload
              </button>
            </div>
            <UploadProgress
              nBytesTotal={inProgressUpload.size}
              nBytesUploaded={inProgressUpload.nBytesUploaded}
            />
          </div>
        ) : (file ? (
          <div className='existing-file'>
            <div className='filename'>{file.name}</div>
            <div className='status'>
              <UploadedFileSelect isReadOnly={isReadOnly} value={value} files={files} onChange={this.onChange} />
              <p className='file-select-button'>
                <label htmlFor={fieldId}>
                  Replace
                </label>
                <input
                  name={name}
                  type='file'
                  id={fieldId}
                  readOnly={isReadOnly}
                  onChange={this.onChangeFileInput}
                />
              </p>
            </div>
            <hr />
          </div>
        ) : (
          <div className='no-file'>
            <p>Drag file here</p>
            <p>or</p>
            <p className='file-select-button'>
              <label htmlFor={fieldId}>
                Browse
              </label>
              <input
                name={name}
                type='file'
                id={fieldId}
                readOnly={isReadOnly}
                onChange={this.onChangeFileInput}
              />
            </p>
          </div>
        ))}
        <div className='drop-here'>
          <p>Drop file here</p>
        </div>
      </div>
    )
  }
}
