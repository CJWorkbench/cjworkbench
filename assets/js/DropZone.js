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
    req.end(function(err,response){
        console.log("upload done!!!!!");
    });
  }

  render(){
    return(
      <div>
        <Dropzone
            onDrop={this.onDrop}
            wfModuleId={this.props.wfModuleId}>
          <div>Try dropping some files here, or click to select files to upload.</div>
        </Dropzone>
      </div>
          );
  }
}