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
    this.initFields(props);
    this.click = this.click.bind(this);
    this.changeParam = this.changeParam.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
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
      showButtons: false,
      showNotes:  ( this.wf_module.notes
                    && (this.wf_module.notes != "")
                    && (this.wf_module.notes != "Write notes here")
                  ),  // only show on load if a note exists & not default text
      showEditableNotes: false,             // do not display in edit state on initial load
      notifications: this.wf_module.notifications,
      notification_count: this.wf_module.notification_count,
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
    store.dispatch(clearNotificationsAction(this.wf_module.id));
    this.clickNotification();
  }

  // alas, the drawback of the convienence of initFields is we need to call it whenever props change
  componentWillReceiveProps(newProps) {
    this.initFields(newProps);
    if (newProps['data-wfmodule'].is_collapsed !== this.state.isCollapsed) {
      this.setState({
        isCollapsed: newProps['data-wfmodule'].is_collapsed
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
    if (this.props['data-selected']) {
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
    store.dispatch(setSelectedWfModuleAction(this.wf_module.id));
  }

  changeParam(id, payload) {
    this.props['data-changeParam'](id, payload)
  }

  // These functions allow parameters to access each others value (text params only)
  // Used e.g. for custom UI elements to save/restore their state from hidden parameters
  // Suppresses reassignment of the same text, which can be important to avoid endless notification loops
  setParamText(paramIdName, text) {
    var p = this.params.find( p => p.parameter_spec.id_name == paramIdName );
    if (p && text != p.string) {
      this.props['data-changeParam'](p.id, { value: text })
    }
  }

  getParamText(paramIdName) {
    var p = this.params.find( p => p.parameter_spec.id_name == paramIdName );
    if (p) {
      return p.value;
    }
  }

  removeModule(e) {
    this.props['data-removeModule'](this.wf_module.id);
  }

  // Optimistically updates the state, and then sends the new state to the server,
  // where it's persisted across sessions and through time.
  toggleCollapsed(e) {
    e.stopPropagation();
    store.dispatch( setWfModuleCollapsedAction(this.wf_module.id, !this.state.isCollapsed, this.props['data-isReadOnly']) );
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  showNotes(e) {
    e.stopPropagation();
    this.setState({ showNotes: true,  showEditableNotes: !this.props['data-isReadOnly'] });
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
        this.wf_module.id,
        { notifications: !this.wf_module.notifications }
    ));
  }

  setModuleRef(ref) {
    this.moduleRef = ref;
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
          changeParam={this.changeParam}
          wf_module_id={this.wf_module.id}
          revision={this.revision}
          updateSettings={updateSettings}
          getParamText={this.getParamText}
          setParamText={this.setParamText}
          setClickNotification={this.setClickNotification}
          notifications={this.props['data-wfmodule'].notifications}
          loggedInUser={this.props['data-user']}
          startDrag={this.props.startDrag}
          stopDrag={this.props.stopDrag}
        />)
      });

    var inside;
    if (!this.state.isCollapsed)
      inside =  <div className='module-card-params'>
                  <div className='module-description'>
                    {this.wf_module.module_version.module.description}
                  </div>
                  {paramdivs}
                </div>;

    var notes;
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
              </div>;

    var helpIcon;
    if (!this.props['data-isReadOnly'])
      helpIcon =  <a className='btn help-button d-flex align-items-center'
                      href={this.module.help_url} target="_blank">
                    <div className='icon-help' />
                  </a>;

    var notesIcon;
    if (!this.state.showNotes && !this.props['data-isReadOnly'])
      notesIcon = <div className='context-button btn' onClick={this.showNotes}>
                    <div className='icon-note btn icon-l-gray ' />
                  </div>;

    var contextMenu;
    if(!this.props['data-isReadOnly'])
      contextMenu = <WfModuleContextMenu
          removeModule={ () => this.removeModule() }
          stopProp={(e) => e.stopPropagation()}
          id={this.wf_module.id}
          className=''
        />;


    // Set opacity to 0/1 instead of just not rendering these elements, so that any children that these
    // buttons create (e.g. export dialog) are still visible. Can't use display: none as we need display: flex
    // Fixes https://www.pivotaltracker.com/story/show/154033690
    var contextBtns =
        <div className='d-flex align-items-center' style={{ opacity: this.state.showButtons ? '1' : '0' }} >
          <div>{helpIcon}</div>
          <div>{notesIcon}</div>
          <div>{contextMenu}</div>
        </div>

    var moduleIcon = 'icon-' + this.module.icon + ' WFmodule-icon mr-2';

    // Putting it all together: name, status, parameters, output
    // For testing: connectDropTarget and connectDragSource will return null because they're provided as mock functions,
    // so if this outputs 'undefined' we return null
    return this.props.connectDropTarget(this.props.connectDragSource(
      // Removing this outer div breaks the drag and drop animation for reasons
      // that aren't clear right now. It doesn't hurt anything but it shouldn't
      // be necessary either.
      <div onClick={this.click} className={(this.props.isOver ? ('over ' + this.state.dragPosition) : '')}>
        {notes}
        <div className='wf-card mx-auto' ref={this.setModuleRef}>

          <div>
            <div className='output-bar-container'>
              <StatusBar status={this.wf_module.status} isSelected={this.props['data-selected']}/>
            </div>
            <div className='card-block p-0' onMouseEnter={this.showButtons} onMouseLeave={this.hideButtons}>
              <div className='module-card-info'>
                <div className={'module-card-header' + (this.props.isDragging ? ' dragging' : '')}>
                  <div className='module-header-content'>
                    <div className='d-flex justify-content-start align-items-center'>
                      <div className={moduleIcon} />
                      <div className='t-d-gray WFmodule-name'>{this.module.name}</div>
                      {this.props['data-wfmodule'].notifications &&
                      <div className={'notification-badge' + (this.props['data-wfmodule'].notification_count > 0 ? ' active t-f-blue' : '' )}>
                        <div
                          className="icon-notification notification-badge-icon ml-3 mr-1"
                          onClick={this.onClickNotification} />
                        {this.props['data-wfmodule'].notification_count > 0 &&
                        <div>{this.props['data-wfmodule'].notification_count}</div>
                        }
                      </div>
                      }
                      <div style={{ opacity: this.state.showButtons ? '1' : '0' }} className={
                        this.state.isCollapsed ?
                          'icon-sort-down btn context-collapse-button' :
                          'icon-sort-up btn context-collapse-button'
                        }
                        onClick={this.toggleCollapsed} >
                      </div>

                    </div>
                    {contextBtns}
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
              } />

          </div>
        </div>
      </div>
    )) || null;
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
  'connectDragSource':  PropTypes.func,
  'connectDropTarget':  PropTypes.func,
  'connectDragPreview':  PropTypes.func,
  'focusModule':        PropTypes.func
};

export { WfModule };
export default sortableWfModule(WfModule);
