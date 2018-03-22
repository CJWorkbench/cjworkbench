import { DropTarget, DragSource } from 'react-dnd'
import flow from 'lodash.flow'
import { findDOMNode } from 'react-dom'
import {store, reorderWfModulesAction, insertPlaceholderAction, reorderPlaceholderAction} from "../workflow-reducer";
import debounce from 'lodash/debounce'

export const targetSpec = {
  canDrop(props, monitor) {
    return monitor.getItemType() === 'module' ||
      (monitor.getItemType() === 'notification' && props.loads_data && !props['data-wfmodule'].notifications);
  },

  drop(props, monitor, component) {
    if (monitor.getItemType() === 'module') {
      const source = monitor.getItem();
      const target = props.index;
      return {
        source,
        target
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
      const sourceIndex = monitor.getItem().index;
      const targetIndex = props.index;
      if (sourceIndex === targetIndex) {
        return;
      }
      const targetBoundingRect = findDOMNode(component).getBoundingClientRect();
      const targetMiddleY = (targetBoundingRect.bottom - targetBoundingRect.top) / 2;
      const mouseY = monitor.getClientOffset();
      const targetClientY = mouseY.y - targetBoundingRect.top;

      if (sourceIndex === false) {
        store.dispatch(insertPlaceholderAction(monitor.getItem(), targetIndex));
        monitor.getItem().index = targetIndex;
      } else {

        // dragging down
        if (sourceIndex < targetIndex && targetClientY < targetMiddleY) {
          return;
        }

        // dragging up
        if (sourceIndex > targetIndex && targetClientY > targetMiddleY) {
          return;
        }

        store.dispatch(reorderPlaceholderAction(sourceIndex, targetIndex));
        monitor.getItem().index = targetIndex;
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
      index: false,
      id: props['data-wfmodule'].module_version.module.id,
      name: props['data-wfmodule'].module_version.module.name,
      icon: props['data-wfmodule'].module_version.module.icon,
      insert: true,
      wfModuleId: props['data-wfmodule'].id,
    }
  },
  endDrag(props, monitor) {
    if (monitor.didDrop()) {
      const {source} = monitor.getDropResult();
      store.dispatch(reorderWfModulesAction(source.wfModuleId, source.index));
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