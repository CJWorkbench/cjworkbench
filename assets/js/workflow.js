// This is the main script for the Workflow view

import React from 'react'
import { sortable } from 'react-sortable'
import ModuleLibrary from './ModuleLibrary'
import { WorkflowNavBar } from './navbar'
import WfModule from './WfModule'
import OutputPane from './OutputPane'
import PropTypes from 'prop-types'
import EditableWorkflowName from './EditableWorkflowName'
import {
  Button,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter
} from 'reactstrap'
import WfContextMenu from './WfContextMenu'

import { getPageID, csrfToken } from './utils'

// Are these Require statements redundant?
require('bootstrap/dist/css/bootstrap.css');
require('../css/style.css');


// ---- Sortable WfModules within the workflow ----
var SortableWfModule= sortable(WfModule);

var SortableList = React.createClass({

  getInitialState: function() {
    return {
      draggingIndex: null,
    };
  },

  updateState: function(newState) {
    this.setState(newState);

    // If we've ended a drag, we need to post the new order to the server
    if (newState.draggingIndex === null) {

      // Generate a JSON payload that has only module ID and order, then PATCH
      var newOrder = this.props.data.wf_modules.map( (item, i) => ({id: item.id, order: i}) )

      fetch('/api/workflows/' + getPageID(), {
        method: 'patch',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(newOrder) })
      .catch( (error) => { console.log('Request failed', error); });
    }
  },

  render: function() {
    var listItems = this.props.data.wf_modules.map(function(item, i) {
      return (
        <SortableWfModule
          key={item.id}
          updateState={this.updateState}
          items={this.props.data.wf_modules}
          draggingIndex={this.state.draggingIndex}
          sortId={i}
          outline="list"
          childProps={{
            'isReadOnly': this.props.data.read_only,
            'data-wfmodule': item,
            'data-changeParam': this.props.changeParam,
            'data-removeModule': this.props.removeModule,
            'data-revision': this.props.data.revision,
            'data-selected': (item.id == this.props.selected_wf_module)
          }}
        />
      );
    }, this);

    return (
          <div className="list">{listItems}</div>
    )
  }
});

// ---- WorkflowMain ----


export default class Workflow extends React.Component {

  constructor(props: iProps) {
    super(props);
    this.state = {
      moduleLibraryVisible: false,
      isPublic: false,
      privacyModalOpen: false
    };
    this.toggleModuleLibrary = this.toggleModuleLibrary.bind(this);
    this.setPublic = this.setPublic.bind(this);
    this.togglePrivacyModal = this.togglePrivacyModal.bind(this);
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.workflow === undefined) {
      return false;
    }

    this.setState({
      isPublic: nextProps.workflow.public
    });
  }

  // toggles the Module Library between visible or not
  toggleModuleLibrary() {
    this.setState(oldState => ({
      moduleLibraryVisible: !oldState.moduleLibraryVisible
    }));
  }

  setPublic(isPublic) {
    fetch('/api/workflows/' + getPageID(), {
      method: 'post',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({'public': isPublic}) })
    .then( () => {
      this.setState({isPublic: isPublic});
    })
    .catch( (error) => { console.log('Request failed', error); })
  }

  togglePrivacyModal() {
    this.setState({ privacyModalOpen: !this.state.privacyModalOpen });
  }

  renderPrivacyModal() {
    if (!this.state.privacyModalOpen) {
      return null;
    }

    return (
      <Modal isOpen={this.state.privacyModalOpen} toggle={this.togglePrivacyModal}>
        <ModalHeader toggle={this.togglePrivacyModal} className='dialog-header' >
          <span className='t-d-gray title-4'>Privacy Setting</span>
          <span className='icon-close' onClick={this.togglePrivacyModal}></span>
        </ModalHeader>
        <ModalBody className='dialog-body'>
          <div className="row">
            <div className="col-sm-4">
              <div className={"action-button " + (this.state.isPublic ? "button-full-blue" : "button-gray") } onClick={() => {this.setPublic(true); this.togglePrivacyModal()}}>Public</div>
            </div>
            <div className="col-sm-8">
              <p>Anyone can access and duplicate the workflow or any of its modules</p>
            </div>
          </div>
          <br></br>
          <div className="row">
            <div className="col-sm-4">
              <div className={"action-button " + (!this.state.isPublic ? "button-full-blue" : "button-gray")} onClick={() => {this.setPublic(false); this.togglePrivacyModal()}}>Private</div>
            </div>
            <div className="col-sm-8">
              <p>Only you can access and edit he workflow</p>
            </div>
          </div>
        </ModalBody>
      </Modal>
    );
  }

  render() {
    // Wait until we have a workflow to render
    if (this.props.workflow === undefined) {
      return null;
    }

    var outputPane = null;
    if (this.props.workflow.wf_modules.length > 0) {
      outputPane = <OutputPane id={this.props.selected_wf_module} revision={this.props.workflow.revision}/>
    }

    var moduleLibrary = <ModuleLibrary
          addModule={module_id => this.props.addModule(module_id,
                        this.props.workflow.wf_modules.length)}
          toggleModuleLibrary={this.toggleModuleLibrary}
          workflow={this} // We pass the workflow down so that we can toggle the module library visibility in a sensible manner.
          />

    // Choose whether we want to display the Module Library or the Output Pane.
    var displayPane = null;
    if (this.state.moduleLibraryVisible) {
        displayPane = moduleLibrary;
    } else {
      displayPane = outputPane;
    }

    let privacyModal = this.renderPrivacyModal();

    // Takes care of both, the left-hand side and the right-hand side of the
    // UI. The modules in the workflow are displayed on the left (vertical flow)
    // and the output of the modules on the right.
    // Instead of the output, we see the Module Library UI if the user
    // invokes the Module Library.
    return (
      <div className="workflow-root">
        <WorkflowNavBar workflowId={this.props.workflow.id} api={this.props.api} /><div className="workflow-container">
          <div className="modulestack-left ">
            <div className="modulestack-header w-75 mx-auto ">
              <div className="d-flex justify-content-between">
                <div>Back to Workflows</div>
                {!this.props.workflow.read_only > 0 &&
                  <WfContextMenu
                    deleteWorkflow={ () => this.deleteWorkflow(listValue.id) }
                    shareWorkflow={ () => this.togglePublic(this.props.workflow.public) }
                  />
                }
              </div>
              <br></br>
              <div className="d-flex justify-content-between">
                <div>
                <EditableWorkflowName
                  value={this.props.workflow.name}
                  editClass='editable-title-field title-1 t-d-gray'
                  wfId={this.props.workflow.id}
                  isReadOnly={this.props.workflow.read_only} />
                <ul className="list-inline list-workflow-meta">
                  <li className="list-inline-item">by <strong>{this.props.workflow.owner_name}</strong></li>
                  <li className="list-inline-item">updated <strong>{this.props.workflow.last_update}</strong></li>
                  <li className="list-inline-item" onClick={this.togglePrivacyModal}><strong className='t-f-blue'>{this.state.isPublic ? 'public' : 'private'}</strong></li>
                </ul>
                {privacyModal}
                </div>
                <Button onClick={this.toggleModuleLibrary.bind(this)}
                    className='button-blue action-button'>Add Module</Button>
              </div>
            </div>
            <div className="modulestack-list w-75 mx-auto ">
              <SortableList
                data={this.props.workflow}
                selected_wf_module={this.props.selected_wf_module}
                changeParam={this.props.changeParam}
                removeModule={this.props.removeModule}
              />
            </div>
          </div>
          <div className="outputpane-right">
            {displayPane}
          </div>
        </div>
      </div>
    );
  }
}

Workflow.propTypes = {
  api:                PropTypes.object.isRequired,
  workflow:           PropTypes.object,             // not required as fetched after page loads
  selected_wf_module: PropTypes.number,
  addModule:          PropTypes.func.isRequired,
  removeModule:       PropTypes.func.isRequired
};
