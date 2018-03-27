import { DropTarget, DragSource } from 'react-dnd'
import flow from 'lodash.flow'
import { findDOMNode } from 'react-dom'
import {store, reorderWfModulesAction, insertPlaceholderAction, reorderPlaceholderAction} from "../workflow-reducer";
import debounce from 'lodash/debounce'

export const targetSpec = {
  canDrop(props, monitor) {
    return monitor.getItemType() === 'module' ||
      (monitor.getItemType() === 'notification' && props.loads_data && !props.wfModule.notifications);
  },

  drop(props, monitor, component) {
    if (monitor.getItemType() === 'module') {
      const source = monitor.getItem();
      source.target = props.index;
      // If we're dragging up and we're dropping on the bottom half of the target:
      if (component.state.dragPosition === 'bottom') {
        source.target += 1;
      }
      source.position = component.state.dragPosition;
      return {
        source
      }
    }

    if (monitor.getItemType() === 'notification') {
      component.setNotifications();
      return {
        notifications: true
      }
    }
  },

  hover(props, monitor, component) {
    if (monitor.getItemType() === 'module') {
      const targetBoundingRect = component.moduleRef.getBoundingClientRect();
      const targetMiddleY = (targetBoundingRect.bottom - targetBoundingRect.top) / 2;
      const mouseY = monitor.getClientOffset();
      const targetClientY = mouseY.y - targetBoundingRect.top;

      if (targetClientY > targetMiddleY && component.state.dragPosition !== 'bottom') {
        component.setState({
          dragPosition: 'bottom'
        });
      }

      if (targetClientY < targetMiddleY && component.state.dragPosition !== 'top') {
        component.setState({
          dragPosition: 'top'
        });
      }
    }
  }
};

export function targetCollect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
    dragItem: monitor.getItem(),
    dragItemType: monitor.getItemType()
  }
}

export const sourceSpec = {
  beginDrag(props) {
    return {
      type: 'module',
      index: props.index,
      id: props.wfModule.module_version.module.id,
      name: props.wfModule.module_version.module.name,
      icon: props.wfModule.module_version.module.icon,
      insert: true,
      wfModuleId: props.wfModule.id
    }
  },
  endDrag(props, monitor) {
    if (monitor.didDrop()) {
      const { source } = monitor.getDropResult();
      store.dispatch(reorderWfModulesAction(source.wfModuleId, source.target, source.position));
    }
  },
  // when False, drag is disabled
  canDrag: function(props) {
    return props.canDrag;
  }
};

export function sourceCollect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource(),
    connectDragPreview: connect.dragPreview(),
    isDragging: monitor.isDragging()
  }
}

export const sortableWfModule = flow(
  DropTarget(['module', 'notification'], targetSpec, targetCollect),
  DragSource('module', sourceSpec, sourceCollect)
);