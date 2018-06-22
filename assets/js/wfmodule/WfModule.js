// UI for a single module within a workflow

import React from 'react'
import DataVersionModal from '../DataVersionModal'
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
import { connect } from 'react-redux'
import lessonSelector from '../lessons/lessonSelector'


// ---- WfModule ----
export class WfModule extends React.PureComponent {
  static propTypes = {
    isReadOnly:         PropTypes.bool.isRequired,
    isAnonymous:        PropTypes.bool.isRequired,
    index:              PropTypes.number.isRequired,
    wfModule:           PropTypes.object,
    selected:           PropTypes.bool,
    changeParam:        PropTypes.func,
    removeModule:       PropTypes.func,
    api:                PropTypes.object.isRequired,
    onDragStart:        PropTypes.func.isRequired, // func({ type:'WfModule',id,index }) => undefined
    onDragEnd:          PropTypes.func.isRequired, // func() => undefined
    focusModule:        PropTypes.func,
    isLessonHighlight: PropTypes.bool.isRequired,
    isLessonHighlightNotes: PropTypes.bool.isRequired,
    isLessonHighlightCollapse: PropTypes.bool.isRequired,
    revision:           PropTypes.number.isRequired,
    onClearNotifications: PropTypes.func.isRequired, // func() => undefined
  }

  constructor(props) {
    super(props);

    this.click = this.click.bind(this);
    this.changeParam = this.changeParam.bind(this);
    this.setParamText = this.setParamText.bind(this);
    this.getParamText = this.getParamText.bind(this);
    this.getParamMenuItems = this.getParamMenuItems.bind(this);
    this.removeModule = this.removeModule.bind(this);
    this.setNotifications = this.setNotifications.bind(this);
    this.setModuleRef = this.setModuleRef.bind(this);
    this.moduleRef = null;
    this.notesInputRef = React.createRef();

    this.state = {
      isCollapsed: this.props.wfModule.is_collapsed,
      notes: this.props.wfModule.notes || '',
      isNoteForcedVisible: false,
      notifications: this.props.wfModule.notifications,
      hasUnseenNotification: this.props.wfModule.has_unseen_notification,
      isDataVersionModalOpen: false,
      isDragging: false,
    }
  }

  clickNotification() {
    return false;
  }

  onClickNotification = () => {
    this.props.onClearNotifications(this.props.wfModule.id)
    this.setState({
      isDataVersionModalOpen: true,
    })
  }

  componentWillReceiveProps(newProps) {
    if (newProps.wfModule.is_collapsed !== this.state.isCollapsed) {
      this.setState({
        isCollapsed: newProps.wfModule.is_collapsed
      })
    }
  }

  // Scroll when we create a new wfmodule
  componentDidMount() {
    if (this.props.selected) {
      this.props.focusModule(this.moduleRef);
    }
  }

  // We become the selected module on any click
  click(e) {
    store.dispatch(setSelectedWfModuleAction(this.props.index));
  }

  changeParam(id, payload) {
    this.props.changeParam(id, payload)
  }

  onDragStart = (ev) => {
    if (ev.target.tagName in {
      'button': null,
      'input': null,
      'select': null,
      'textarea': null,
      'label': null,
    }) {
      // Don't drag when user selects text
      ev.preventDefault()
      return
    }

    const dragObject = {
      type: 'WfModule',
      index: this.props.index,
      id: this.props.wfModule.id,
    }
    ev.dataTransfer.setData('application/json', JSON.stringify(dragObject))
    ev.dataTransfer.effectAllowed = 'move'
    ev.dataTransfer.dropEffect = 'move'
    this.props.onDragStart(dragObject)

    this.setState({
      isDragging: true,
    })
  }

  onDragEnd = (ev) => {
    this.props.onDragEnd()

    this.setState({
      isDragging: false,
    })
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

  getParamId = (paramIdName) => {
    var p = this.props.wfModule.parameter_vals.find( p => p.parameter_spec.id_name == paramIdName );
    if (p) {
      return p.id;
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
  setCollapsed(isCollapsed) {
    this.setState({
      isCollapsed,
    })

    store.dispatch(setWfModuleCollapsedAction(
      this.props.wfModule.id,
      isCollapsed,
      this.props.isReadOnly
    ))
  }

  collapse = () => {
    this.setCollapsed(true)
  }

  expand = () => {
    this.setCollapsed(false)
  }

  // when Notes icon is clicked, show notes and start in editable state if not read-only
  focusNote = () => {
    const ref = this.notesInputRef.current;
    if (ref) {
      this.setState({ isNoteForcedVisible: true });
      ref.focus();
      ref.select();
    }
  }

  onChangeNote = (ev) => {
    this.setState({ notes: ev.target.value });
  }

  onFocusNote = () => {
    this.setState({ isNoteForcedVisible: true });
  }

  onBlurNote = (ev) => {
    if (this.state.notes !== (this.props.wfModule.notes || '')) {
      // TODO use a reducer action
      this.props.api.setWfModuleNotes(this.props.wfModule.id, this.state.notes);
    }
    this.setState({ isNoteForcedVisible: false })
  }

  onCancelNote = (ev) => {
    this.setState({ notes: this.props.wfModule.notes });
  }

  setNotifications() {
    store.dispatch(
      updateWfModuleAction(
        this.props.wfModule.id,
        { notifications: !this.props.wfModule.notifications }
    ));
  }

  onCloseDataVersionModal = () => {
    this.setState({
      isDataVersionModalOpen: false,
    })
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
          moduleName={module.name}
          isReadOnly={this.props.isReadOnly}
          key={i}
          p={ps}
          changeParam={this.changeParam}
          wf_module_id={wfModule.id}
          revision={this.props.revision}
          updateSettings={updateSettings}
          getParamId={this.getParamId}
          getParamText={this.getParamText}
          getParamMenuItems={this.getParamMenuItems}
          setParamText={this.setParamText}
          notifications={wfModule.notifications}
        />)
      });

    const notes = (
      <div className={`module-notes${(!!this.state.notes || this.state.isNoteForcedVisible) ? ' visible' : ''}`}>
        <EditableNotes
          isReadOnly={this.props.isReadOnly}
          inputRef={this.notesInputRef}
          placeholder='Type something'
          value={this.state.notes}
          onChange={this.onChangeNote}
          onFocus={this.onFocusNote}
          onBlur={this.onBlurNote}
          onCancel={this.onCancelNote}
          />
      </div>
    );

    let alertButton;
    if (!this.props.isReadOnly && !this.props.isAnonymous) {
      let className = 'notifications'
      if (this.state.notifications) className += ' enabled'
      if (this.state.hasUnseenNotification) className += ' has-unseen'
      const title = this.state.notifications ? 'Email alerts enabled' : 'Email alerts disabled'

      alertButton = (
        <button title={title} className={className} onClick={this.onClickNotification}>
          <i className="icon-notification"></i>
          { this.state.hasUnseenNotification ? <span className="has-unseen"></span> : null }
        </button>
      );
    }

    let helpIcon;
    if (!this.props.isReadOnly) {
      helpIcon = (
        <a title='Help for this module' className='help-button' href={module.help_url} target='_blank'>
          <i className='icon-help'></i>
        </a>
      );
    }

    let notesIcon;
    if (!this.props.isReadOnly) {
      notesIcon = (
        <button
          title="Edit Note"
          className={'btn edit-note' + (this.props.isLessonHighlightNotes ? ' lesson-highlight' : '')}
          onClick={this.focusNote}
          >
          <i className='icon-note'></i>
        </button>
      );
    }

    var contextMenu;
    if(!this.props.isReadOnly)
      contextMenu = <WfModuleContextMenu
          removeModule={ () => this.removeModule() }
          stopProp={(e) => e.stopPropagation()}
          id={wfModule.id}

        />;


    // Set opacity to 0/1 instead of just not rendering these elements, so that any children that these
    // buttons create (e.g. export dialog) are still visible. Can't use display: none as we need display: flex
    // Fixes https://www.pivotaltracker.com/story/show/154033690
    const contextBtns =
        <div className='context-buttons'>
          {alertButton}
          {helpIcon}
          {notesIcon}
          {contextMenu}
        </div>

    const moduleIcon = 'icon-' + module.icon + ' WFmodule-icon';

    let maybeDataVersionModal = null
    if (this.state.isDataVersionModalOpen) {
      maybeDataVersionModal = (
        <DataVersionModal
          wfModuleId={wfModule.id}
          notificationsEnabled={wfModule.notifications}
          onClose={this.onCloseDataVersionModal}
          />
      )
    }

    // Putting it all together: name, status, parameters, output
    return (
      <div onClick={this.click} className={'wf-module' + (this.props.isLessonHighlight ? ' lesson-highlight' : '') + (this.state.isCollapsed ? ' collapsed' : ' expanded')} data-module-name={module.name}>
        {notes}
        <div className={'wf-card '+ (this.state.isDragging ? 'dragging ' : '')} ref={this.setModuleRef} draggable={!this.props.isReadOnly} onDragStart={this.onDragStart} onDragEnd={this.onDragEnd}>

          <div>
            <div className='output-bar-container'>
              <StatusBar status={wfModule.status} isSelected={this.props.selected} isDragging={this.state.isDragging}/>
            </div>
            <div className='module-content'>
              <div className='module-card-header'>
                <WfModuleCollapseButton
                  isCollapsed={this.state.isCollapsed}
                  isLessonHighlight={this.props.isLessonHighlightCollapse}
                  onCollapse={this.collapse}
                  onExpand={this.expand}
                  />
                <i className={moduleIcon}></i>
                <div className='module-name'>{module.name}</div>
                {contextBtns}
              </div>
              {/* --- Error message --- */}
              <StatusLine status={wfModule.status} error_msg={wfModule.error_msg} />
              <div className='module-card-params'>
                {paramdivs}
              </div>
            </div>
          </div>
        </div>
        {maybeDataVersionModal}
      </div>
    )
  }
}

class WfModuleCollapseButton extends React.PureComponent {
  static propTypes = {
    isCollapsed: PropTypes.bool.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    onCollapse: PropTypes.func.isRequired, // func() => undefined
    onExpand: PropTypes.func.isRequired, // func() => undefined
  }

  render() {
    const { isCollapsed, isLessonHighlight, onCollapse, onExpand } = this.props

    const iconClass = isCollapsed ? 'icon-sort-right' : 'icon-sort-down'
    const onClick = isCollapsed ? onExpand : onCollapse
    const name = isCollapsed ? 'expand module' : 'collapse module'
    const lessonHighlightClass = isLessonHighlight ? 'lesson-highlight' : ''
    return (
      <button name={name} className="wf-module-collapse" onClick={onClick}>
        <i className={`context-collapse-button ${iconClass} ${lessonHighlightClass}`}></i>
      </button>
    )
  }
}

function propsToModuleName(props) {
  return (
    props.wfModule
    && props.wfModule.module_version
    && props.wfModule.module_version.module
    && props.wfModule.module_version.module.name
    || ''
  )
}

function mapStateToProps(state, ownProps) {
  const { testHighlight } = lessonSelector(state)
  const moduleName = propsToModuleName(ownProps)
  return {
    isLessonHighlight: testHighlight({ type: 'WfModule', moduleName }),
    isLessonHighlightCollapse: testHighlight({ type: 'WfModuleContextButton', button: 'collapse', moduleName }),
    isLessonHighlightNotes: testHighlight({ type: 'WfModuleContextButton', button: 'notes', moduleName }),
    isReadOnly: state.workflow.read_only,
    isAnonymous: state.workflow.is_anonymous,
  }
}

// TODO replace all "store.dispatch" above with mapDispatchToProps()
function mapDispatchToProps(dispatch) {
  return {
    onClearNotifications(wfModuleId) {
      store.dispatch(clearNotificationsAction(wfModuleId))
    },
  }
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(WfModule)
