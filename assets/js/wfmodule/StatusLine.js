// ---- StatusLine ----

// Display error message, if any
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
import React from "react";
import PropTypes from "prop-types";

export default class StatusLine extends React.Component {
  render() {
    if (this.props.status == 'error') {
      return <div className='wf-module-error-msg mb-3'>{this.props.error_msg}</div>
    // } else if (this.props.status == 'busy') {
    //   return <div className='wf-module-error-msg mb-3'>Working...</div>
    } else {
      return false
    }
  }
}

StatusLine.PropTypes = {
  status: PropTypes.string,
  error_msg: PropTypes.string
}