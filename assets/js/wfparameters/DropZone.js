import React, {Component} from 'react';
//import Dropzone from 'react-dropzone';
import {store, setWfModuleStatusAction} from '../workflow-reducer'
import {csrfToken} from '../utils'
import FineUploaderTraditional from 'fine-uploader-wrappers'
import Dropzone from 'react-fine-uploader/dropzone'
import FileInput from 'react-fine-uploader/file-input'
import ProgressBar from 'react-fine-uploader/progress-bar'
import Filename from 'react-fine-uploader/filename'

import 'react-fine-uploader/gallery/gallery.css'

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


    constructor(props) {
        super(props)
        this.state = {
            files: [],
            submittedFiles: [],
            filename: ''
        }

        this.uploader = new FineUploaderTraditional({
            options: {
                request: {
                    endpoint: '/api/uploadfile',
                    customHeaders: {
                        'X-CSRFToken': csrfToken
                    },
                    filenameParam: 'name',
                    inputName: 'file',
                    uuidName: 'uuid',
                    totalFileSizeName: 'size',
                    params: {
                        'wf_module': this.props.wfModuleId
                    }
                },
                session: {
                    endpoint: '/api/uploadfile',
                    customHeaders: {
                        'X-CSRFToken': csrfToken
                    },
                    params: {
                        'wf_module': this.props.wfModuleId
                    }
                },
                multiple: false
            }
        })
    }

    update_filename(err, res){
      if (err === null) {
        this.setState({
          filename: res[0].name,
        })
      } else {
        console.warn(err)
      }
    }

    componentDidUpdate(prevProps) {
      if (prevProps.revision !== this.props.revision) {
        this.props.api._fetch(`/api/uploadfile?wf_module=${this.props.wfModuleId}`)
          .then(
            res => this.update_filename(null, res),
            err => this.update_filename(err, null)
          )
      }
    }

    componentDidMount() {
        this.uploader.on('statusChange', (id, oldStatus, newStatus) => {
            if (newStatus === 'submitted') {
                store.dispatch(setWfModuleStatusAction(this.props.wfModuleId, 'busy'))
                const submittedFiles = [id]
                this.setState({submittedFiles})
            }
            else if (newStatus === 'upload successful') {
                const files = [id]
                const submittedFiles = []
                const filename = this.uploader.methods.getName(id)
                this.setState({files, submittedFiles, filename})
            }
            else if (newStatus === 'canceled') {
                const submittedFiles = []
                this.setState({submittedFiles})
            }
        })
    }

    render() {
      // Classe names are in brackets becaue of : --->> [Fine Uploader 5.15.3] Caught exception in 'onStatusChange' callback - input is a void element tag and must neither have `children` nor use `dangerouslySetInnerHTML`. Check the render method of DropZone.
        return (
            <div className={""}>
                {this.state.files.length == 0 ? (
                    <div>
                      <Dropzone
                        className={"dropzone d-flex justify-content-center align-items-center"}
                        multiple={false}
                        uploader={this.uploader}>
                        <div className={"content-3 ml-4 mr-2"}>Drag file here, or&nbsp;</div>
                        <FileInput className={"content-3 action-link"} multiple={false}
                                   uploader={this.uploader}>Browse</FileInput>
                      </Dropzone>
                      {
                          this.state.submittedFiles.map(id => (
                              <div
                                  className={"loader-empty react-fine-uploader-gallery-total-progress-bar-container"}
                                  key={id}>
                                  <ProgressBar className={"react-fine-uploader-gallery-total-progress-bar"} id={id}
                                               uploader={this.uploader} hideBeforeStart={true} hideOnComplete={true}/>
                              </div>
                          ))
                      }
                    </div>
                ) : (
                    <div>
                      <div className={"upload-box"}>
                        <div>
                          <div className={"label-margin t-d-gray content-3"}>File name</div>
                          <div className={"t-d-gray content-3 text-field-readonly"}>{this.state.filename}</div>
                        </div>
                          <FileInput className={"button-blue dropzone-button action-button"} multiple={false}
                                     uploader={this.uploader}>Replace</FileInput>
                        </div>
                        {
                          this.state.submittedFiles.map(id => (
                              <div className={"loader-replace react-fine-uploader-gallery-progress-bar-container"} key={id}>
                                  <ProgressBar id={id} className={"react-fine-uploader-gallery-total-progress-bar"}
                                               uploader={this.uploader} hideBeforeStart={true} hideOnComplete={true}/>
                              </div>
                          ))
                        }
                    </div>
                )}
            </div>
        )

    }

}
