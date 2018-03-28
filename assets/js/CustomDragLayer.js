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
        willChange: 'transform',
        display: 'none',
      };
    }

    const { x, y } = getSourceClientOffset;
    const transform = `translate3d(${x}px, ${y}px, 0)`;
    return {
      willChange: 'transform',
      transform: transform,
      WebkitTransform: transform
    };
  }

  render() {
    return (
      <div style={{
        position: 'fixed',
        zIndex: 10000,
        pointerEvents: 'none'
      }}>
        <div style={this.getItemStyles(this.props)}>
          {this.props.item &&
          <WfModuleHeader moduleName={this.props.item.name} moduleIcon={this.props.item.icon} />}
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
    getSourceClientOffset: monitor.getClientOffset(),
  }
}

CustomDragLayer.PropTypes = {
  isDragging: PropTypes.bool,
  itemType: PropTypes.string,
  item: PropTypes.shape({
    name: PropTypes.string,
    icon: PropTypes.string
  }),
  getSourceClientOffset: PropTypes.shape({
    x: PropTypes.number,
    y: PropTypes.number
  })
};

export { CustomDragLayer }; // Export un-decorated component for testing
export default DragLayer(collect)(CustomDragLayer);
