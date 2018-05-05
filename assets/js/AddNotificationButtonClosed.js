/**
 * Component which can be dragged to a data import module
 *     to attach a notification
 */

import React from 'react';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';
import { store, updateWfModuleAction } from "./workflow-reducer";

// TODO: gather all functions for dragging into one utility file
const spec = {
  beginDrag(props, monitor, component) {
    return {
      index: false,
      id: props.id,
      insert: true,
    }
  }
}

function collect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    isDragging: monitor.isDragging()
  }
}

class AddNotificationButtonClosed extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      showButton: false
    };
    this.showButton = this.showButton.bind(this);
    this.hideButton = this.hideButton.bind(this);
    this.handleClick = this.handleClick.bind(this);
  }

  showButton() {
    this.setState({showButton: true});
    // tell parent to close any open Module Categories
    this.props.setOpenCategory(null);
  }

  hideButton() {
    this.setState({showButton: false});
  }

  handleClick() {
    let state = store.getState();
    let dataModule = state.workflow.wf_modules.find((wfmodule) => {
       return wfmodule.module_version.module.loads_data === true;
    });

    if (typeof dataModule === 'undefined') return;
    if (dataModule.notifications === true) return;

    store.dispatch(updateWfModuleAction(dataModule.id, {
        notifications: true
    }));
  }

  render() {

    var popout =
      <div
        className='card alert-closed-ML'
        style={{ display: this.state.showButton ? 'block' : 'none' }}
      >
        <div className='ML-module d-flex '>
          <div className='content-5  my-auto mr-5'>Add data alert</div>
          <div className='ml-handle'>
            <div className='icon-grip'></div>
          </div>
        </div>
      </div>

    return this.props.connectDragSource(
      <div
        className='notification-button-closed'
        onMouseEnter={this.showButton}
        onMouseLeave={this.hideButton}
        onClick={this.handleClick}
      >
        <div className='card'>
          <div className='closed-ML--category t-vl-gray'>
            <div className='ml-icon-container' >
              <div className="icon-notification ml-icon" title='Add Notification'></div>
            </div>
          </div>
        </div>
        {popout}
      </div>
    )
  }
}

export default DragSource('notification', spec, collect)(AddNotificationButtonClosed)

AddNotificationButtonClosed.propTypes = {
  setOpenCategory:  PropTypes.func.isRequired
};
