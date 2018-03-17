// workflow.page.js - the master JavaScript for /workflows/N

import React from 'react'
import ReactDOM from 'react-dom'
import { Provider, connect } from 'react-redux'
import * as Actions from '../workflow-reducer'
import { getPageID, csrfToken } from '../utils'
import Workflow from '../workflow'
import workbenchAPI from '../WorkbenchAPI'
import { DragDropContextProvider } from 'react-dnd'
import HTML5Backend from 'react-dnd-html5-backend'

require('bootstrap/dist/css/bootstrap.css');
require('../../css/style.scss');

// Global API object, encapsulates all calls to the server
const api = workbenchAPI();

// ---- Workflow container ----

// Handles addModule (and any other actions that change top level workflow state)
const mapStateToProps = (state) => {
  return {
    workflow: state.workflow,
    selected_wf_module: state.selected_wf_module,
    loggedInUser: state.loggedInUser,
    // This is the top level dependency injection for all API calls on this page
    api: api
  }
};

const mapDispatchToProps = (dispatch) => {
  return {
    addModule: (moduleId, insertBefore) => {
      dispatch(Actions.addModuleAction(moduleId, insertBefore))
    },
    removeModule: (wfModuleId) => {
      dispatch(Actions.deleteModuleAction(wfModuleId))
    },
    changeParam: (paramId, newVal) => {
      dispatch(Actions.setParamValueAction(paramId, newVal))
    }
  }
};

const WorkflowContainer = connect(
  mapStateToProps,
  mapDispatchToProps
)(Workflow)



// --- Websocket handling ----

// Start listening for events
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socket = new WebSocket(protocol + "//" + window.location.host + "/workflows/" + getPageID());

socket.onmessage = function(e) {
  var data = JSON.parse(e.data);
  if ('type' in data) {
    switch (data.type) {

      case 'wfmodule-status':
        Actions.store.dispatch(Actions.setWfModuleStatusAction(data.id, data.status, data.error_msg ? data.error_msg : ''));
        return

      case 'reload-workflow':
        Actions.store.dispatch(Actions.reloadWorkflowAction());
        return
    }
  }
}


// --- Main ----

// Render with Provider to root so all objects in the React DOM can access state
ReactDOM.render(
    <Provider store={Actions.store}>
      <DragDropContextProvider backend={HTML5Backend}>
        <WorkflowContainer/>
      </DragDropContextProvider>
    </Provider>,
    document.getElementById('root')
);

// Load the page, Select the first module in the workflow (if one exists, else shows Module Library)
Actions.store.dispatch(Actions.initialLoadWorkflowAction());

// Start Intercom, if we're that sort of installation
//// We are indeed: Very mission, much business!
if (window.APP_ID) {
  if (window.initState.loggedInUser) {
    window.Intercom("boot", {
      app_id: window.APP_ID,
      email: window.initState.loggedInUser.email,
      user_id: window.initState.loggedInUser.id,
      alignment: 'left',
      horizontal_padding: 30,
      vertical_padding: 20
    });
  } else {
    // no one logged in -- viewing read only workflow
    window.Intercom("boot", {
      app_id: window.APP_ID,
      alignment: 'left',
      horizontal_padding: 30,
      vertical_padding: 20
    });
  }
}
