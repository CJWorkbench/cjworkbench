// Wraps all API calls. Useful both to centralize and abstract these calls,
// also for dependency injection for testing

import { csrfToken } from './utils'

// All API calls which fetch data return a promise which returns JSON
class WorkbenchAPI {

  onParamChanged(paramID, newVal) {
    return (
      fetch('/api/parameters/' + paramID, {
        method: 'patch',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(newVal)
      }));
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
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
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
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          notes: text
        })
      }))
  }

  setWfName(wfId, newName) {
    return (
      fetch('/api/workflows/' + wfId, {
        method: 'post',
        credentials: 'include',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
          newName: newName
        })
      })
    )
  }

  // setWfModuleUpdateSettings(wf_module_id, ___) {
  //   return (
  //     fetch('/api/wfmodules/' + wf_module_id, {
  //       method: 'patch',
  //       credentials: 'include',
  //       headers: {
  //         'Accept': 'application/json',
  //         'Content-Type': 'application/json',
  //         'X-CSRFToken': csrfToken
  //       },
  //       body: JSON.stringify({
  //         'auto_update_data' : True,
  //         'update_interval'  : 5,
  //         'update_units'     : 'weeks' 
  //       })
  //     })
  //   )
  // }

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
}

// Singleton API object for global use
const api = new WorkbenchAPI();
export default () => { return api; }
