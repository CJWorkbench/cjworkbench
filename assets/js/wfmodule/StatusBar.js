// ---- StatusBar ----

import React from "react";
import PropTypes from "prop-types";

export default class StatusBar extends React.Component {
  render() {

    let barColor = undefined;

    switch (this.props.status) {
      case 'ready':
        barColor = (this.props.isSelected) ? 'module-output-bar-blue' : 'module-output-bar-white'
        break;
      case 'busy':
        barColor = 'module-output-bar-orange';
        break;
      case 'error':
        barColor = (this.props.isSelected) ? 'module-output-bar-red' : 'module-output-bar-pink'
        break;
      default:
        barColor = 'module-output-bar-white';
        break;
    }

    return <div className={barColor} />
  }
}

StatusBar.PropTypes = {
  isSelected: PropTypes.bool,
  status: PropTypes.string
};