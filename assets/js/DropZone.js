import React,{Component} from 'react';
//import Dropzone from 'react-dropzone';
import request from 'superagent';
import { csrfToken } from './utils'

import FineUploaderTraditional from 'fine-uploader-wrappers'
import Gallery from 'react-fine-uploader'
import Thumbnail from 'react-fine-uploader/thumbnail'
import Dropzone from 'react-fine-uploader/dropzone'
import FileInput from 'react-fine-uploader/file-input'


// ...or load this specific CSS file using a <link> tag in your document
import 'react-fine-uploader/gallery/gallery.css'



export default class DropZone extends Component{
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
            deleteFile: {
                enabled: true,
                endpoint: '/api/uploadfile',
                customHeaders: {
                    'X-CSRFToken': csrfToken
                }
            },
            validation: {
                allowedExtensions: ['csv', 'CSV', 'xls', 'xlsx', 'XLS', 'XLSX']
            },
            multiple: false
        }
    })
  }

  render(){
    return(
        <Gallery uploader={ this.uploader } />
      )
  }
}
