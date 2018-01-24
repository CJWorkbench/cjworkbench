/**
 * Component which can be dragged to a data import module
 *     to attach a notification
 * 
 * For opened version of Module Library
 */

import React from 'react';
import PropTypes from 'prop-types'
import { DragSource } from 'react-dnd';

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

class AddNotificationButtonOpen extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {

    return this.props.connectDragSource(
      <div className='card'>
        <div className='second-level t-vl-gray d-flex'>
          <div className='d-flex flex-row align-items-center'>
            <div className='ml-icon-container ml-2'>
              <div className="icon-notification ml-icon"></div>
            </div>
            <div className='content-5 ml-module-name'>Add data alert</div>
          </div>
          <div className='ml-handle'>
            <div className='icon-grip'></div>
          </div>
        </div>
      </div>
    )
  }
}

export default DragSource('notification', spec, collect)(AddNotificationButtonOpen)

