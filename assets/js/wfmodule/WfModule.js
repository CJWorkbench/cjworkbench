// UI for a single module within a workflow

import React from 'react'
import WfParameter from '../WfParameter'
import WfModuleContextMenu from '../WfModuleContextMenu'
import EditableNotes from '../EditableNotes'
import StatusBar from './StatusBar'
import StatusLine from './StatusLine'
import {
  store,
  setWfModuleCollapsedAction,
  updateWfModuleAction,
  clearNotificationsAction,
  setSelectedWfModuleAction
} from '../workflow-reducer'
import PropTypes from 'prop-types'
import { getEmptyImage } from 'react-dnd-html5-backend'
import { sortableWfModule } from "./WfModuleDragDropConfig";


// Libraries to provide a collapsible table view
import { Collapse } from 'reactstrap';


// ---- WfModule ----
class WfModule extends React.Component {

  constructor(props) {
    super(props);
    this.click = this.click.bind(this);
    this.changeParam = this.changeParam.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.getParamMenuItems = this.getParamMenuItems.bind(this);
    this.removeModule = this.removeModule.bind(this);
    this.showNotes = this.showNotes.bind(this);
    this.hideNotes = this.hideNotes.bind(this);
    this.showButtons = this.showButtons.bind(this);
    this.hideButtons = this.hideButtons.bind(this);
    this.toggleCollapsed = this.toggleCollapsed.bind(this);
    this.setNotifications = this.setNotifications.bind(this);
    this.setClickNotification = this.setClickNotification.bind(this);
    this.onClickNotification = this.onClickNotification.bind(this);
    this.setModuleRef = this.setModuleRef.bind(this);
    this.moduleRef = null;
  }

  componentWillMount() {
    this.setState({
      isCollapsed: this.props.wfModule.is_collapsed,
      showButtons: false,
      showNotes:  ( this.props.wfModule.notes
                    && (this.props.wfModule.notes != "")
                    && (this.props.wfModule.notes != "Write notes here")
                  ),  // only show on load if a note exists & not default text
      showEditableNotes: false,             // do not display in edit state on initial load
      notifications: this.props.wfModule.notifications,
      notification_count: this.props.wfModule.notification_count,
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
    store.dispatch(clearNotificationsAction(this.props.wfModule.id));
    this.clickNotification();
  }

  componentWillReceiveProps(newProps) {
    if (newProps.wfModule.is_collapsed !== this.state.isCollapsed) {
      this.setState({
        isCollapsed: newProps.wfModule.is_collapsed
      })
    }

    if(!newProps.isDragging && this.state.dragPosition) {
      this.setState({
        dragPosition: null
      })
    }
  }

  // Scroll when we create a new wfmodule
  componentDidMount() {
    if (this.props.selected) {
      this.props.focusModule(this.moduleRef);
    }

		this.props.connectDragPreview(getEmptyImage(), {
			// IE fallback: specify that we'd rather screenshot the node
			// when it already knows it's being dragged so we can hide it with CSS.
			captureDraggingState: true,
		});
  }

  // We become the selected module on any click
  click(e) {
    store.dispatch(setSelectedWfModuleAction(this.props.wfModule.id));
  }

  changeParam(id, payload) {
    this.props.changeParam(id, payload)
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(paramIdName, text) {
    var p = this.props.wfModule.parameter_vals.find( p => p.parameter_spec.id_name == paramIdName );
    if (p && text != p.string) {
      this.props.changeParam(p.id, { value: text })
    }
  }

  getParamText(paramIdName) {
    var p = this.props.wfModule.parameter_vals.find( p => p.parameter_spec.id_name == paramIdName );
    if (p) {
      return p.value;
    }
  }

  getParamMenuItems(paramIdName) {
    var p = this.props.wfModule.parameter_vals.find(p => p.parameter_spec.id_name == paramIdName);
    if(p) {
      if(p.menu_items) {
        return p.menu_items.split('|').map(s => s.trim());
      }
    }
    return [];
  }

  removeModule(e) {
    this.props.removeModule(this.props.wfModule.id);
  }

  // Optimistically updates the state, and then sends the new state to the server,
  // where it's persisted across sessions and through time.
  toggleCollapsed(e) {
    e.stopPropagation();
    store.dispatch( setWfModuleCollapsedAction(this.props.wfModule.id, !this.state.isCollapsed, this.props.isReadOnly) );
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  showNotes(e) {
    e.stopPropagation();
    this.setState({ showNotes: true,  showEditableNotes: !this.props.isReadOnly });
  }

  hideNotes() {
    this.setState({showNotes: false});
  }

  showButtons() {
    this.setState({showButtons: true});
  }

  hideButtons() {
    this.setState({showButtons: false});
  }

  setNotifications() {
    store.dispatch(
      updateWfModuleAction(
        this.props.wfModule.id,
        { notifications: !this.props.wfModule.notifications }
    ));
  }

  setModuleRef(ref) {
    this.moduleRef = ref;
  }

  render() {
    let wfModule = this.props.wfModule;
    let module = wfModule.module_version.module;

    var updateSettings = {
      lastUpdateCheck:  wfModule.last_update_check,
      autoUpdateData:   wfModule.auto_update_data,
      updateInterval:   wfModule.update_interval,
      updateUnits:      wfModule.update_units
    };

    // Each parameter gets a WfParameter
    var paramdivs = wfModule.parameter_vals.map((ps, i) => {
        return (<WfParameter
          api={this.props.api}
          moduleName={this.props.name}
          isReadOnly={this.props.isReadOnly}
          key={i}
          p={ps}
          changeParam={this.changeParam}
          wf_module_id={wfModule.id}
          revision={this.props.revision}
          updateSettings={updateSettings}
          getParamText={this.getParamText}
          getParamMenuItems={this.getParamMenuItems}
          setParamText={this.setParamText}
          setClickNotification={this.setClickNotification}
          notifications={wfModule.notifications}
          loggedInUser={this.props.user}
          startDrag={this.props.startDrag}
          stopDrag={this.props.stopDrag}
        />)
      });

    var inside;
    if (!this.state.isCollapsed)
      inside =  <div className='module-card-params'>
                  {paramdivs}
                  <div className='module-description'>
                    {module.description}
                  </div>
                </div>;

    var notes;
    var value = ( wfModule.notes && (wfModule.notes != "") )
      ? wfModule.notes
      : "Write notes here";

    if (this.state.showNotes)
      notes = <div className='module-notes'>
                <EditableNotes
                  api={this.props.api}
                  isReadOnly={this.props.isReadOnly}
                  value={value}
                  hideNotes={ () => this.hideNotes() }
                  wfModuleId={wfModule.id}
                  startFocused={this.state.showEditableNotes}
                />
              </div>;

    var helpIcon;
    if (!this.props.isReadOnly)
      helpIcon =  <button className='context-button btn'>
                    <a className='help-button d-flex align-items-center'
                        href={module.help_url} target="_blank">
                      <div className='icon-help' />
                    </a>
                  </button>

    var notesIcon;
    if (!this.state.showNotes && !this.props.isReadOnly)
      notesIcon = <button className='context-button btn edit-note' onClick={this.showNotes}>
                    <div className='icon-note icon-l-gray ' />
                  </button>;

    var contextMenu;
    if(!this.props.isReadOnly)
      contextMenu = <WfModuleContextMenu
          removeModule={ () => this.removeModule() }
          stopProp={(e) => e.stopPropagation()}
          id={wfModule.id}
          className=''
        />;


    // Set opacity to 0/1 instead of just not rendering these elements, so that any children that these
    // buttons create (e.g. export dialog) are still visible. Can't use display: none as we need display: flex
    // Fixes https://www.pivotaltracker.com/story/show/154033690
    const contextBtns =
        <div className='context-buttons--container'>
          {wfModule.notifications &&
          <div className={'notification-badge' + (wfModule.notification_count > 0 ? ' active t-f-blue' : '' )}>
            <div
              className="icon-notification notification-badge-icon ml-3 mr-1"
              onClick={this.onClickNotification} />
            {wfModule.notification_count > 0 &&
            <div>{wfModule.notification_count}</div>
            }
          </div>
          }
          <div style={{ opacity: this.state.showButtons ? '1' : '0' }}>{helpIcon}</div>
          <div style={{ opacity: this.state.showButtons ? '1' : '0' }}>{notesIcon}</div>
          <div style={{ opacity: this.state.showButtons ? '1' : '0' }}>{contextMenu}</div>
        </div>

    const moduleIcon = 'icon-' + module.icon + ' WFmodule-icon mr-2';

    // Putting it all together: name, status, parameters, output
    // For testing: connectDropTarget and connectDragSource will return null because they're provided as mock functions,
    // so if this outputs 'undefined' we return null
    return this.props.connectDropTarget(this.props.connectDragSource(
      // Removing this outer div breaks the drag and drop animation for reasons
      // that aren't clear right now. It doesn't hurt anything but it shouldn't
      // be necessary either.
      <div onClick={this.click} className={'wf-module' + (this.props.isOver ? (' over ' + this.state.dragPosition) : '')}>
        {notes}
        <div className={'wf-card mx-auto '+ (this.props.isDragging ? 'wf-module--dragging ' : '')} ref={this.setModuleRef}>

          <div>
            <div className='output-bar-container'>
              <StatusBar status={wfModule.status} isSelected={this.props.selected} isDragging={this.props.isDragging}/>
            </div>
            <div className='card-block p-0' onMouseEnter={this.showButtons} onMouseLeave={this.hideButtons}>
              <div className='module-card-info'>
                <div className='module-card-header'>
                  <div className='module-header-content'>
                    <div className='module-id--group' onClick={this.toggleCollapsed}>
                      <div className={moduleIcon} />
                      <div className='t-d-gray WFmodule-name'>{module.name}</div>
                      <div style={{ opacity: this.state.showButtons ? '0' : '0' }} className={
                        this.state.isCollapsed ?
                          'icon-sort-down context-collapse-button' :
                          'icon-sort-up context-collapse-button'
                        }>
                      </div>
                    </div>
                    {contextBtns}
                  </div>
                </div>
                {/* --- Module content when expanded --- */}
                <Collapse className='' isOpen={!this.state.isCollapsed} >
                  {/* --- Error message --- */}
                  <StatusLine status={wfModule.status} error_msg={wfModule.error_msg} />

                  {inside}
                </Collapse>
              </div>
            </div>

            <div className={
              'drop-alert ' +
              ( (this.props.dragItemType === 'notification' && this.props.canDrop && this.props.dragItem) ? 'active ' : '' ) +
              ( (this.props.dragItemType === 'notification' && this.props.canDrop && this.props.isOver) ? 'over ' : '')
              } />

          </div>
        </div>
      </div>
    )) || null;
  }
}

WfModule.propTypes = {
  isReadOnly:         PropTypes.bool.isRequired,
  wfModule:           PropTypes.object,
  revison:            PropTypes.number,
  selected:           PropTypes.bool,
  changeParam:        PropTypes.func,
  removeModule:       PropTypes.func,
  api:                PropTypes.object.isRequired,
  connectDragSource:  PropTypes.func,
  connectDropTarget:  PropTypes.func,
  connectDragPreview: PropTypes.func,
  focusModule:        PropTypes.func
};

export { WfModule };
export default sortableWfModule(WfModule);
