/**
 * Component which can be dragged to a data import module
 *     to attach a notification
 */

import React from 'react';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';

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
  }

  showButton() {
    this.setState({showButton: true});
  }

  hideButton() {
    this.setState({showButton: false});
  }

  render() {

    var button =
      <div 
        className='card notification-button-popout' 
        style={{ display: this.state.showButton ? 'block' : 'none' }}
        onMouseEnter={this.showButton} 
        onMouseLeave={this.hideButton}
      >
        <div className='second-level d-flex '>
          <div className='content-5 ml-module-name my-auto mr-3'>Add data alert</div>
          <div className='icon-grip my-auto'></div>
        </div>
      </div>

    return this.props.connectDragSource(
      <div >
        <div className='card notification-button-closed' onMouseEnter={this.showButton} onMouseLeave={this.hideButton}>
          <div className='second-level t-vl-gray d-flex'>
            <div className='ml-icon-container mr-5' >
              <div className="icon-notification ml-icon" title='Add Notification'></div>
            </div>
          </div>
        </div>
        {button}
      </div>      
    )
  }
}

export default DragSource('notification', spec, collect)(AddNotificationButtonClosed)
