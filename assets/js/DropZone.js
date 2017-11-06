import React, {Component} from 'react';
//import Dropzone from 'react-dropzone';
import request from 'superagent';
import {store, wfModuleStatusAction} from './workflow-reducer'
import {csrfToken} from './utils'

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

        this.update_filename = this.update_filename.bind(this);

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
                validation: {
                    allowedExtensions: ['csv', 'CSV', 'xls', 'xlsx', 'XLS', 'XLSX']
                },
                multiple: false
            }
        })
    }

    update_filename(err, res){
        var filename = '';
        if (res.ok) {
            if (JSON.parse(res.text).length > 0)
                filename = JSON.parse(res.text)[0]['name']
            this.setState({filename});
        }
    }

    componentWillReceiveProps(nextProps) {
        if (this.props.revision != nextProps.revision) {
            var req = request
                    .get('/api/uploadfile')
                    .query({'wf_module': this.props.wfModuleId})
                    .set('X-CSRFToken', csrfToken);
            req.end((err, res)=> this.update_filename(err, res));
        }
    }

    componentDidMount() {
        this.uploader.on('statusChange', (id, oldStatus, newStatus) => {
            if (newStatus === 'submitted') {
                store.dispatch(wfModuleStatusAction(this.props.wfModuleId, 'busy'))
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
        return (
            <div>
                {this.state.files.length == 0 ? (
                    <div>
                        <Dropzone
                            className={"dropzone parameter-margin d-flex justify-content-center align-items-center"}
                            multiple={false}
                            uploader={this.uploader}>
                            <div className={"title-3 ml-4"}>Drag file here, or&nbsp;</div>
                            <FileInput className={"button-blue action-button mt-0"} multiple={false}
                                       uploader={this.uploader}>Click to select</FileInput>
                        </Dropzone>
                        {
                            this.state.submittedFiles.map(id => (
                                <div
                                    className={"parameter-margin react-fine-uploader-gallery-total-progress-bar-container"}
                                    key={id}>
                                    <ProgressBar className={"react-fine-uploader-gallery-total-progress-bar"} id={id}
                                                 uploader={this.uploader} hideBeforeStart={true} hideOnComplete={true}/>
                                </div>
                            ))
                        }
                    </div>
                ) : (
                    <div>
                        <div className={"parameter-margin upload-box"}>
                            <div className={""}>
                                <div className={"label-margin t-d-gray content-3"}>File name:</div>
                                <div className={"t-d-gray content-3 mb-3"}>{this.state.filename}</div>
                            </div>
                            <FileInput className={"button-blue action-button mt-0"} multiple={false}
                                       uploader={this.uploader}>Change file</FileInput>
                        </div>
                        {
                            this.state.submittedFiles.map(id => (
                                <div className={"parameter-margin react-fine-uploader-gallery-progress-bar-container"}
                                     key={id}>
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
