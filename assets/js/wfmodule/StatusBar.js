// ---- StatusBar ----

import React from "react";
import PropTypes from "prop-types";

export default class StatusBar extends React.Component {
  render() {

    let barColor = undefined;

    switch (this.props.status) {
      case 'ready':
        barColor = (this.props.isSelected) ? 'module-output--selected' : 'module-output-bar-white'
        break;
      case 'busy':
        barColor = 'module-output-bar-orange';
        break;
      case 'error':
        barColor = (this.props.isSelected) ? 'module-output--error-selected' : 'module-output--error'
        break;
      default:
        barColor = 'module-output-bar-white';
        break;
    }

    return <div className={barColor + (this.props.isDragging ? ' wf-module--dragging ' : '')} />
  }
}

StatusBar.PropTypes = {
  isDragging: PropTypes.bool,
  isSelected: PropTypes.bool,
  status: PropTypes.string
};
