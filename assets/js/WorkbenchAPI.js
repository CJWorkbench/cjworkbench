// Wraps all API calls. Useful both to centralize and abstract these calls,
// also for dependency injection for testing

import { csrfToken } from './utils'

const apiHeaders = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'X-CSRFToken': csrfToken
};

// All API calls which fetch data return a promise which returns JSON
class WorkbenchAPI {

  listWorkflows() {
    return (
      fetch('/api/workflows', {credentials: 'include'})
      .then(response => response.json())
    )
  }

  loadWorkflow(workflowId) {
    return (
      fetch('/api/workflows/' + workflowId, { credentials: 'include'})
      .then(response => response.json())
    )
  }

  newWorkflow(newWorkflowName) {
    return (
      fetch('/api/workflows',
        {
          method: 'post',
          credentials: 'include',
          headers: apiHeaders,
          body: JSON.stringify({name: newWorkflowName})
        })
      .then(response => response.json()))
  }

  deleteWorkflow(workflowId) {
    return (
      fetch(
        '/api/workflows/' + workflowId ,
        {
          method: 'delete',
          credentials: 'include',
          headers: {
            'X-CSRFToken': csrfToken
          }
        }
      )
    )
  }

  addModule(workflowId, moduleId, insertBefore) {
    return (
      fetch(
        '/api/workflows/' + workflowId + "/addmodule",
        {
          method: 'put',
          credentials: 'include',
          headers: apiHeaders,
          body: JSON.stringify({insertBefore: insertBefore, moduleId: moduleId})
        }
      ).then(response => response.json())
    )
  }

  deleteModule(wfModuleId) {
    return (
      fetch('/api/wfmodules/' + wfModuleId, {
        method: 'delete',
        credentials: 'include',
        headers: {'X-CSRFToken': csrfToken}
      }));
  }

  setWorkflowPublic(workflowID, isPublic) {
    return (
      fetch('/api/workflows/' + workflowID, {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({'public': isPublic})
      }));
  }

  onParamChanged(paramID, newVal) {
    return (
      fetch('/api/parameters/' + paramID, {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify(newVal)
      }));
  }

  render(wf_module_id, startrow, endrow) {
    var url = '/api/wfmodules/' + wf_module_id + '/render';

    if (startrow || endrow) {
      url += "?";
      if (startrow) {
        url += "startrow=" + startrow;
      }
      if (endrow) {
        if (startrow)
          url += "&";
        url += "endrow=" + endrow;
      }
    }

    return (
      fetch(url, {credentials: 'include'})
      .then(response => response.json())
    )
  }

  input(wf_module_id) {
    return (
      fetch('/api/wfmodules/' + wf_module_id + '/input', {credentials: 'include'})
      .then(response => response.json())
    )
  }

  // All available modules in the system
  getModules() {
    return (
      fetch('/api/modules/', { credentials: 'include' })
      .then(response => response.json())
    )
  }

  getWfModuleVersions(wf_module_id) {
    // NB need parens around the contents of the return, or this will fail miserably (return undefined)
    return (
        fetch('/api/wfmodules/' + wf_module_id + '/dataversions', {credentials: 'include'})
        .then(response => response.json())
    )
  }

  setWfModuleVersion(wf_module_id, version) {
    return (
      fetch('/api/wfmodules/' + wf_module_id + '/dataversions', {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          selected: version
        })
      }))
  }

  setWfModuleNotes(wf_module_id, text) {
    return (
      fetch('/api/wfmodules/' + wf_module_id, {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          notes: text
        })
      }))
  }


  setWfModuleCollapsed(wf_module_id, isCollapsed) {
    return fetch('/api/wfmodules/' + wf_module_id, {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          collapsed: isCollapsed
        })
      })
  }

  setWfName(wfId, newName) {
    return (
      fetch('/api/workflows/' + wfId, {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          newName: newName
        })
      })
    )
  }

  setWfLibraryCollapse(workflow_id, isCollapsed) {
    return (
      fetch('/api/workflows/' + workflow_id, {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          module_library_collapsed: isCollapsed
        })
      })
    )
  }

  setSelectedWfModule(workflow_id, module_id) {
    return (
      fetch('/api/workflows/' + workflow_id, {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          selected_wf_module: module_id
        })
      })
    )
  }

  // Params should be an object matching format below
  setWfModuleUpdateSettings(wf_module_id, params) {
    return (
      fetch('/api/wfmodules/' + wf_module_id, {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify({
          'auto_update_data' : params.auto_update_data,  // bool
          'update_interval'  : params.update_interval,   // int
          'update_units'     : params.update_units       // str
        })
      })
    )
  }

  updateWfModule(wf_module_id, params) {
    return(
      fetch('/api/wfmodules/' + wf_module_id, {
        method: 'patch',
        credentials: 'include',
        headers: apiHeaders,
        // Don't validate here, but possibly filter out props not in
        // a hardcoded list later
        body: JSON.stringify(params)
      })
    )
  }

  undo(workflow_id) {
    return (
      fetch('/api/workflows/' + workflow_id + '/undo', {
        method: 'put',
        credentials: 'include',
        headers: {
          'X-CSRFToken': csrfToken
        }
      }))
  }

  redo(workflow_id) {
    return (
      fetch('/api/workflows/' + workflow_id + '/redo', {
        method: 'put',
        credentials: 'include',
        headers: {
          'X-CSRFToken': csrfToken
        }
      }))
  }

  duplicateWorkflow(workflow_id) {
    return (
      fetch('/api/workflows/' + workflow_id + '/duplicate', {credentials: 'include'})
        .then(response => response.json())
    )
  }

  currentUser() {
    return (
      fetch('/api/user/', {credentials: 'include'})
        .then(response => response.json())
    )
  }

  disconnectCurrentUser(id) {
    return (
      fetch('/api/user/google_credentials', {
        credentials: 'include',
        method: 'delete',
        headers: apiHeaders,
        body: JSON.stringify({
          credentialId: id
        })
      }).then(response => response.json())
    )
  }

  deleteWfModuleNotifications(wf_module_id) {
    return (
      fetch('/api/wfmodules/' + wf_module_id + '/notifications', {
        credentials: 'include',
        method: 'delete',
        headers: apiHeaders
      }).then(response => response.json())
    )
  }

  importFromGithub(eventData) {
    return (
      fetch('/api/importfromgithub/', {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify(eventData)
      }).then(response => response.json())
    )
  }

  // This is Bad. You should get a list of serialized data versions on the
  // workflow module instead of a 2-tuple, and there should be a generic
  // data version create/read/update/delete method. As there should be for
  // every object in the database.
  markDataVersionsRead(wf_module_id, data_versions) {
    return (
      fetch('/api/wfmodules/' + wf_module_id + '/dataversion/read', {
        credentials: 'include',
        method: 'patch',
        headers: apiHeaders,
        body: JSON.stringify({
          versions: data_versions
        })
      })
    )
  }

  postParamEvent(paramId, data) {
    return (
      fetch( '/api/parameters/' + paramId + '/event', {
        method: 'post',
        credentials: 'include',
        headers: apiHeaders,
        body: JSON.stringify(data)
      }).then((response) => {
        if (response.status === 204) {
          //Don't try to parse JSON if we got an empty response
          return {};
        } else {
          return response.json();
        }
      })
    )
  }

}

// Singleton API object for global use
const api = new WorkbenchAPI();
export default () => { return api; }
