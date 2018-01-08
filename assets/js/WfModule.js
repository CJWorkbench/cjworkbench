// UI for a single module within a workflow

import React from 'react'
import WfParameter from './WfParameter'
import TableView from './TableView'
import WfModuleContextMenu from './WfModuleContextMenu'
import EditableNotes from './EditableNotes'
import { store, wfModuleStatusAction } from './workflow-reducer'
import { findDOMNode } from 'react-dom'
import * as Actions from './workflow-reducer'
import PropTypes from 'prop-types'
import { DropTarget, DragSource } from 'react-dnd'
import flow from 'lodash.flow'

// Libraries to provide a collapsable table view
import { Collapse, Button, CardBlock, Card } from 'reactstrap';

// ---- StatusBar ----

class StatusBar extends React.Component {
  render() {

    var barColor = undefined;

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

    return <div className={barColor}></div>
  }
}

// ---- StatusLine ----

// Display error message, if any
// BUG - Tying this to Props will ensure that error message stays displayed, even after resolution
class StatusLine extends React.Component {
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

// ---- WfModule ----

const targetSpec = {
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
      // getBoundingClientRect almost certainly doesn't
      // work consistently in all browsers. Replace!
      const targetBoundingRect = findDOMNode(component).getBoundingClientRect();
      const targetMiddleY = (targetBoundingRect.bottom - targetBoundingRect.top) / 2;
      const mouseY = monitor.getClientOffset();
      const targetClientY = mouseY.y - targetBoundingRect.top;

      if (sourceIndex === false) {
        props.dragNew(targetIndex, monitor.getItem());
        monitor.getItem().index = targetIndex;
        return;
      } else {

        // dragging down
        if (sourceIndex < targetIndex && targetClientY < targetMiddleY) {
          return;
        }

        // dragging up
        if (sourceIndex > targetIndex && targetClientY > targetMiddleY) {
          return;
        }

        props.drag(sourceIndex, targetIndex);
        monitor.getItem().index = targetIndex;
      }
    }
  }
}

function targetCollect(connect, monitor) {
  return {
    connectDropTarget: connect.dropTarget(),
    isOver: monitor.isOver(),
    canDrop: monitor.canDrop(),
    dragItem: monitor.getItem(),
    dragItemType: monitor.getItemType()
  }
}

const sourceSpec = {
  beginDrag(props, monitor, component) {
    return {
      index: props.index
    }
  },
  endDrag(props, monitor, component) {
    if (monitor.didDrop()) {
      const {source, target} = monitor.getDropResult();
      props.drop();
    }
  }
}

function sourceCollect(connect, monitor) {
  return {
    connectDragSource: connect.dragSource()
  }
}

class WfModule extends React.Component {

  constructor(props) {
    super(props);
    this.initFields(props);
    this.click = this.click.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.removeModule = this.removeModule.bind(this);
    this.showNotes = this.showNotes.bind(this);
    this.hideNotes = this.hideNotes.bind(this);
    this.showArrow = this.showArrow.bind(this);
    this.hideArrow = this.hideArrow.bind(this);
    this.toggleCollapsed = this.toggleCollapsed.bind(this);
    this.setNotifications = this.setNotifications.bind(this);
    this.setClickNotification = this.setClickNotification.bind(this);
    this.onClickNotification = this.onClickNotification.bind(this);
  }

  // our props are annoying (we use data- because Sortable puts all these props om the DOM object)
  // so save them into this

  // TODO: We're not using Sortable anymore, remove this.
  initFields(props) {
    this.wf_module = props['data-wfmodule'];
    this.module = this.wf_module.module_version.module;
    this.params = this.wf_module.parameter_vals;
    this.revision = props['data-revision'];
  }

  componentWillMount() {
    this.setState({
      isCollapsed: this.wf_module.is_collapsed,
      showArrow: false,
      showNotes:  ( this.wf_module.notes
                    && (this.wf_module.notes != "")
                    && (this.wf_module.notes != "Write notes here")
                  ),  // only show on load if a note exists & not default text
      showEditableNotes: false,             // do not display in edit state on initial load
      notifications: this.wf_module.notifications,
      notification_count: this.wf_module.notification_count
    });
  }

  // pass a function to all wf_parameters to allow them to overload
  // the function that runs when a user clicks on the notification
  // icon
  setClickNotification(cb) {
    this.clickNotification = cb;
  }

  clickNotification() {
    return false;
  }

  onClickNotification() {
    Actions.store.dispatch(Actions.clearNotificationsAction(this.wf_module.id));
    this.clickNotification();
  }

  // alas, the drawback of the convienence of initFields is we need to call it whenever props change
  componentWillReceiveProps(newProps) {
    this.initFields(newProps)
  }

  // We become the selected module on any click
  click(e) {
    Actions.store.dispatch(Actions.changeSelectedWfModuleAction(this.wf_module.id));
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(id_name, text) {
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p && text != p.string) {
      this.props['data-changeParam'](p.id, { value: text })
    }
  }

  getParamText(id_name) {
    var p = this.params.find( p => p.parameter_spec.id_name == id_name );
    if (p) {
      return p.value;
    }
  }

  removeModule(e) {
    this.props['data-removeModule'](this.wf_module.id);
  }

  // Optimistically updates the state, and then sends the new state to the server,
  // where it's persisted across sessions and through time.
  toggleCollapsed() {
    var newIsCollapsed = !this.state.isCollapsed;
    this.setState({
      isCollapsed: newIsCollapsed,
    });

    // only want to update the server if we're not in read-only mode.
    if (!this.props['data-isReadOnly']) {
        this.props['data-api'].toggleWfModuleCollapsed(this.wf_module.id, newIsCollapsed);
    }
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  showNotes(e) {
    e.stopPropagation();
    this.setState({ showNotes: true,  showEditableNotes: !this.props['data-isReadOnly'] });
  }

  hideNotes() {
    this.setState({showNotes: false});
  }

  showArrow() {
    this.setState({showArrow: true});
  }

  hideArrow() {
    this.setState({showArrow: false});
  }

  setNotifications() {
    Actions.store.dispatch(
      Actions.updateWfModuleAction(
        this.wf_module.id,
        { notifications: !this.wf_module.notifications }
    ));
  }

  render() {

    var updateSettings = {
      lastUpdateCheck:  this.wf_module.last_update_check,
      autoUpdateData:   this.wf_module.auto_update_data,
      updateInterval:   this.wf_module.update_interval,
      updateUnits:      this.wf_module.update_units
    };

    // Each parameter gets a WfParameter
    var paramdivs = this.params.map((ps, i) => {
        return (<WfParameter
          api={this.props['data-api']}
          isReadOnly={this.props['data-isReadOnly']}
          key={i}
          p={ps}
          changeParam={this.props['data-changeParam']}
          wf_module_id={this.wf_module.id}
          revision={this.revision}
          updateSettings={updateSettings}
          getParamText={this.getParamText}
          setParamText={this.setParamText}
          setClickNotification={this.setClickNotification}
          notifications={this.props['data-wfmodule'].notifications}
          user={this.props['data-user']}
        />)
      });

    var inside = undefined;

    if (!this.state.isCollapsed)
      inside =  <div className='module-card-params'>
                  <div className='module-description'>
                    {this.wf_module.module_version.module.description}
                  </div>
                  {paramdivs}
                </div>;

    var notes = undefined;
    var value = ( this.wf_module.notes && (this.wf_module.notes != "") )
      ? this.wf_module.notes
      : "Write notes here"

    if (this.state.showNotes)
      notes = <div className='module-notes'>
                <EditableNotes
                  api={this.props['data-api']}
                  isReadOnly={this.props['data-isReadOnly']}
                  value={value}
                  hideNotes={ () => this.hideNotes() }
                  wfModuleId={this.wf_module.id}
                  startFocused={this.state.showEditableNotes}
                />
              </div>

    var notesIcon = undefined;
    if (!this.state.showNotes && !this.props['data-isReadOnly'])
      notesIcon = <div className='context-button btn mr-4' onClick={this.showNotes}>
                    <div className='icon-note btn icon-l-gray '></div>
                  </div>

    var contextMenu = undefined;
    if(!this.props['data-isReadOnly'])
      contextMenu = <WfModuleContextMenu
          removeModule={ () => this.removeModule() }
          stopProp={(e) => e.stopPropagation()}
          id={this.wf_module.id}
          className=''
        />

    var modBtn = undefined;
    if (this.state.showArrow) {
      modBtn =
        <div className='d-flex align-items-center'>
          <div className={
            this.state.isCollapsed ?
              'icon-collapse-o btn collapse-button' :
              'icon-collapse btn collapse-button'
            }
            onClick={this.toggleCollapsed} >
          </div>
            <div>{notesIcon}</div>
            <div>{contextMenu}</div>
          </div>
    }


    var moduleIcon = 'icon-' + this.module.icon + ' module-icon mr-3';

    // Putting it all together: name, status, parameters, output
    return (
      // Removing this outer div breaks the drag and drop animation for reasons
      // that aren't clear right now. It doen't hurt anything but it shouldn't
      // be necessary either.
      <div onClick={this.click}>
        <div className='wf-card mx-auto'>
        {this.props.connectDropTarget(this.props.connectDragSource(
          <div>
            <div className='output-bar-container'>
              <StatusBar status={this.wf_module.status} isSelected={this.props['data-selected']}/>
            </div>
            <div className='card-block p-0'onMouseEnter={this.showArrow} onMouseLeave={this.hideArrow}>
              <div className='module-card-info'>
                {notes}
                <div className='module-card-header'>
                  <div className='module-header-content'>
                    <div className='d-flex justify-content-start align-items-center'>
                      <div className={moduleIcon}></div>
                      <div className='t-d-gray title-4 WFmodule-name'>{this.module.name}</div>
                      {this.props['data-wfmodule'].notifications &&
                      <div className={'notification-badge' + (this.props['data-wfmodule'].notification_count > 0 ? ' active t-f-blue' : '' )}>
                        <div
                          className="icon-notification notification-badge-icon ml-3 mr-1"
                          onClick={this.onClickNotification}></div>
                        {this.props['data-wfmodule'].notification_count > 0 &&
                        <div>{this.props['data-wfmodule'].notification_count}</div>
                        }
                      </div>
                      }
                    </div>
                    {/* TODO: not necessary to pass in stopProp*/}
                    <div>
                      {modBtn}
                    </div>
                  </div>
                </div>
                {/* --- Module content when expanded --- */}
                <Collapse className='' isOpen={!this.state.isCollapsed} >
                  {/* --- Error message --- */}
                  <StatusLine status={this.wf_module.status} error_msg={this.wf_module.error_msg} />

                  {inside}
                </Collapse>
              </div>
            </div>

            <div className={
              'drop-alert ' +
              ( (this.props.dragItemType === 'notification' && this.props.canDrop && this.props.dragItem) ? 'active ' : '' ) +
              ( (this.props.dragItemType === 'notification' && this.props.canDrop && this.props.isOver) ? 'over ' : '')
              } ></div>

          </div>
        ))}
        </div>
      </div>
    );
  }
}

WfModule.propTypes = {
  'data-isReadOnly':    PropTypes.bool.isRequired,
  'data-wfmodule':      PropTypes.object,
  'data-revison':       PropTypes.number,
  'data-selected':      PropTypes.bool,
  'data-changeParam':   PropTypes.func,
  'data-removeModule':  PropTypes.func,
  'data-api':           PropTypes.object.isRequired,
  'connectDropTarget':  PropTypes.func,
};

class WfModulePlaceholder extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return this.props.connectDropTarget(this.props.connectDragSource(
      <div className="wf-card placeholder mx-auto"></div>
    ));
  }
}

const sortableComponent = flow(
  DropTarget(['module', 'notification'], targetSpec, targetCollect),
  DragSource('module', sourceSpec, sourceCollect)
);

export const SortableWfModule = sortableComponent(WfModule);
export const SortableWfModulePlaceholder = sortableComponent(WfModulePlaceholder);
