import React from 'react'
import IframeCtrl from './IframeCtrl'

let OutputIframeCtrl;

class OutputIframe extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      src: ("/api/wfmodules/" + this.props.selectedWfModule + "/output?rev=" + this.props.revision)
    }
  }

  componentWillReceiveProps(nextProps) {
    this.setState({
      src: ("/api/wfmodules/" + nextProps.selectedWfModule + "/output?rev=" + nextProps.revision)
    })
  }

  setRef(ref) {
    OutputIframeCtrl = new IframeCtrl(ref);
  }

  render() {
    return <iframe ref={this.setRef} src={this.state.src}></iframe>
  }
}

export {OutputIframe, OutputIframeCtrl}
