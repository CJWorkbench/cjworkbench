import React,{Component} from 'react';
import Dropzone from 'react-dropzone';
import request from 'superagent';
import { csrfToken } from './utils'

export default class DropZone extends Component{
  onDrop(files){
      console.log(this.props.wfModuleId)
    var req=request
              .post('/api/uploadfile/')
              .field('file', files[0])
              .field('wf_module', this.props.wfModuleId)
              .set('X-CSRFToken', csrfToken);
    req.end();
  }

  render(){
    return(
      <div>
        <Dropzone
            onDrop={this.onDrop}
            wfModuleId={this.props.wfModuleId} className="dropzone parameter-margin d-flex justify-content-center align-items-center">
          <div className='icon-add-blue'></div>
          <div className="title-3 ml-4">Drop file here, or click to select</div>
        </Dropzone>
      </div>
          );
  }
}
