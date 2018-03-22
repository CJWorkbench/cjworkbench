import React from 'react';
import PropTypes from 'prop-types';
import { DragLayer } from 'react-dnd';
import WfModuleHeader from './wfmodule/WfModuleHeader';

class CustomDragLayer extends React.Component {
  constructor(props) {
    super(props);
  }

  getItemStyles(props) {
    const { getSourceClientOffset } = props;

    if (!getSourceClientOffset) {
      return {
        display: 'none'
      };
    }

    const { x, y } = getSourceClientOffset;
    const transform = `translate(${x}px, ${y}px)`;
    return {
      transform: transform,
      WebkitTransform: transform
    };
  }

  render() {
    if (this.props.item === null) {
      return null;
    }
    return (
      <div className="drag-layer">
        <div style={this.getItemStyles(this.props)}>
          <WfModuleHeader moduleName={this.props.item.name} moduleIcon={this.props.item.icon} />
        </div>
      </div>
    )
  }
}

function collect(monitor) {
  return {
    isDragging: monitor.isDragging(),
    itemType: monitor.getItemType(),
    item: monitor.getItem(),
    clientOffset: monitor.getClientOffset(),
    getSourceClientOffset: monitor.getSourceClientOffset(),
  }
}

export default DragLayer(collect)(CustomDragLayer);