import React, {Component} from 'react';
import {store, setWfModuleStatusAction} from '../workflow-reducer'
import {csrfToken} from '../utils'
import FineUploaderS3 from 'fine-uploader-wrappers/s3'
import FineUploaderDropZone from 'react-fine-uploader/dropzone'
import FileInput from 'react-fine-uploader/file-input'
import ProgressBar from 'react-fine-uploader/progress-bar'
import Filename from 'react-fine-uploader/filename'

import 'react-fine-uploader/gallery/gallery.css'

const UploadConfig = window.initState ? window.initState.uploadConfig : undefined

export default class DropZone extends Component {
  // onDrop(files){
  //     console.log(this.props.wfModuleId)
  //   var req=request
  //             .post('/api/uploadfile/')
  //             .field('file', files[0])
  //             .field('wf_module', this.props.wfModuleId)
  //             .set('X-CSRFToken', csrfToken);
  //   req.end();
  // }


  state = {
    files: [],
    submittedFileId: null,
    filename: ''
  }

  uploader = new FineUploaderS3({
    options: {
      chunking: {
        enabled: true
      },
      objectProperties: {
        bucket: UploadConfig.bucket,
        key: 'uuid'
      },
      request: {
        accessKey: UploadConfig.accessKey,
        endpoint: `${UploadConfig.server}/${UploadConfig.bucket}`,
        filenameParam: 'name',
        inputName: 'file',
        uuidName: 'uuid',
        totalFileSizeName: 'size'
      },
      signature: {
        endpoint: '/api/uploadfile',
        customHeaders: { 'X-CSRFToken': csrfToken }
      },
      uploadSuccess: {
        endpoint: '/api/uploadfile',
        customHeaders: { 'X-CSRFToken': csrfToken },
        params: {
          'success': true,
          'wf_module': this.props.wfModuleId
        }
      },
      session: {
        endpoint: `/api/uploadfile/${this.props.wfModuleId}`,
        customHeaders: { 'X-CSRFToken': csrfToken }
      },
      multiple: false
    }
  })

  updateFilename (res) {
    this.setState({
      filename: res[0].name,
    })
  }

  componentDidUpdate(prevProps) {
    if (prevProps.lastRelevantDeltaId !== this.props.lastRelevantDeltaId) {
      this.props.api._fetch(`/api/uploadfile?wf_module=${this.props.wfModuleId}`)
        .then(updateFilename, console.warn)
    }
  }

  componentDidMount() {
    this.uploader.on('statusChange', (id, oldStatus, newStatus) => {
      if (newStatus === 'submitted') {
        store.dispatch(setWfModuleStatusAction(this.props.wfModuleId, 'busy'))
        this.setState({ submittedFileId: id })
      }
      else if (newStatus === 'upload successful') {
        this.setState({
          files: [ id ],
          submittedFileId: null,
          filename: this.uploader.methods.getName(id)
        })
      }
      else if (newStatus === 'canceled') {
        this.setState({ submittedFileId: null })
      }
    })
  }

  render() {
    const { files, submittedFileId, filename } = this.state

    const fileInput = (
      <FileInput
        className={files.length ? 'button-blue dropzone-button action-button' : 'content-3 action-link'}
        multiple={false}
        uploader={this.uploader}
      >
        {files.length ? 'Replace' : 'Browse'}
      </FileInput>
    )

    const maybeProgressBar = submittedFileId === null ? null : (
      <div className={`${files.length ? 'loader-replace' : 'loader-empty'} react-fine-uploader-gallery-total-progress-bar-container`}>
        <ProgressBar
          id={submittedFileId}
          className='react-fine-uploader-gallery-total-progress-bar'
          uploader={this.uploader}
          hideBeforeStart
          hideOnComplete
        />
      </div>
    )

    return (
      <div className="uploader">
        {files.length == 0 ? (
          <FineUploaderDropZone
            className='dropzone d-flex justify-content-center align-items-center'
            multiple={false}
            uploader={this.uploader}
          >
            <div className='content-3 ml-4 mr-2'>Drag file here, or&nbsp;</div>
            {fileInput}
          </FineUploaderDropZone>
        ) : (
          <div className='upload-box'>
            <div>
              <div className='label-margin t-d-gray content-3'>File name</div>
              <div className='t-d-gray content-3 text-field-readonly'>{this.state.filename}</div>
            </div>
            {fileInput}
          </div>
        )}
        {maybeProgressBar}
      </div>
    )
  }
}
