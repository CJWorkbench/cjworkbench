// Wraps all API calls. Useful both to centralize and abstract these calls,
// also for dependency injection for testing

import {csrfToken} from './utils'

const apiHeaders = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'X-CSRFToken': csrfToken
};

// All API calls which fetch data return a promise which returns JSON
class WorkbenchAPI {
  /**
   * Returns Promise of JSON on HTTP success (or `null` on HTTP 204 success).
   *
   * The Promise will fail with:
   *
   * * RangeError if the status code is not between 200 and 299.
   * * TypeError if the response Content-Type is not application/json,
   *   or if security checks (like CORS) prevent the fetch.
   * * SyntaxError if the response is invalid JSON.
   */
  _fetch(url, options) {
    const realOptions = Object.assign({ credentials: 'include' }, options || {})
    return fetch(url, realOptions)
      .then(res => {
        if (!res.ok) {
          throw new RangeError(`Server responded with non-200 status code ${res.status}`)
        }
        if (res.headers.get('content-type') && res.headers.get('content-type').toLowerCase().indexOf('application/json') === -1) {
          throw new TypeError("Server response is not JSON", res)
        }
        if (res.status === 204) {
          return null // No content
        }
        return res.json()
      })
  }

  _submit(method, url, body, options) {
    const realOptions = Object.assign(
      { method: method, headers: apiHeaders },
      { body: JSON.stringify(body) },
      options || {}
    )
    return this._fetch(url, realOptions)
  }

  _patch(url, body, options) {
    return this._submit('patch', url, body, options)
  }

  _put(url, body, options) {
    return this._submit('put', url, body, options)
  }

  _post(url, body, options) {
    return this._submit('post', url, body, options)
  }

  _delete(url, options) {
    return this._submit('delete', url, null, { body: '' })
  }

  listWorkflows() {
    return this._fetch('/api/workflows')
  }

  loadWorkflow(workflowId) {
    return this._fetch(`/api/workflows/${workflowId}`)
  }

  newWorkflow(newWorkflowName) {
    return this._post('/api/workflows', { name: newWorkflowName })
  }

  deleteWorkflow(workflowId) {
    return this._delete(`/api/workflows/${workflowId}`)
  }

  reorderWfModules(workflowId, newOrder) {
    return this._patch(`/api/workflows/${workflowId}`, newOrder)
  }

  addModule(workflowId, moduleId, insertBefore) {
    return this._put(`/api/workflows/${workflowId}/addmodule`, {
      insertBefore: insertBefore,
      moduleId: moduleId
    })
  }

  deleteModule(wfModuleId) {
    return this._delete(`/api/wfmodules/${wfModuleId}`)
  }

  setWorkflowPublic(workflowId, isPublic) {
    return this._post(`/api/workflows/${workflowId}`, { 'public': isPublic })
  }

  onParamChanged(paramID, newVal) {
    return this._patch(`/api/parameters/${paramID}`, newVal)
  }

  render(wfModuleId, startrow, endrow) {
    let url = '/api/wfmodules/' + wfModuleId + '/render';

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

    return this._fetch(url)
  }

  input(wfModuleId) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/input`)
  }

  inputColumns(wfModuleId) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/input?startrow=0&endrow=0`)
      .then(json => json.columns)
  }

  output(wfModuleId) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/output`)
  }

  histogram(wfModuleId, column) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/histogram/${column}`)
  }

  getColumns(wfModuleId) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/columns`)
  }

  // All available modules in the system
  getModules() {
    return this._fetch(`/api/modules/`)
  }

  setWfModuleVersion(wfModuleId, version) {
    return this._patch(
      `/api/wfmodules/${wfModuleId}/dataversions`,
      { selected: version }
    )
  }

  setWfModuleNotes(wfModuleId, text) {
    return this._patch(`/api/wfmodules/${wfModuleId}`, { notes: text })
  }


  setWfModuleCollapsed(wfModuleId, isCollapsed) {
    return this._patch(`/api/wfmodules/${wfModuleId}`, { collapsed: isCollapsed })
  }

  setWfName(workflowId, newName) {
    return this._post(`/api/workflows/${workflowId}`, { newName: newName })
  }

  setWfLibraryCollapse(workflowId, isCollapsed) {
    return this._post(`/api/workflows/${workflowId}`, { module_library_collapsed: isCollapsed })
  }

  setSelectedWfModule(workflowId, wfModuleId) {
    return this._post(`/api/workflows/${workflowId}`, { selected_wf_module: wfModuleId })
  }

  updateWfModule(wfModuleId, params) {
    return this._patch(`/api/wfmodules/${wfModuleId}`, params)
  }

  undo(workflowId) {
    return this._put(`/api/workflows/${workflowId}/undo`, null)
  }

  redo(workflowId) {
    return this._post(`/api/workflows/${workflowId}/redo`, null)
  }

  duplicateWorkflow(workflowId) {
    return this._fetch(`/api/workflows/${workflowId}/duplicate`)
  }

  currentGoogleClientAccessToken() {
    return this._fetch('/api/user/google-client-access-token')
  }

  currentUser() {
    return this._fetch('/api/user/')
  }

  disconnectCurrentUser(id) {
    return this._submit('delete', `/api/user/google_credentials`, { credentialId: id })
  }

  deleteWfModuleNotifications(wfModuleId) {
    return this._delete(`/api/wfmodules/${wfModuleId}/notifications`)
  }

  importFromGithub(eventData) {
    return this._post(`/api/importfromgithub/`, eventData)
  }

  // This is Bad. You should get a list of serialized data versions on the
  // workflow module instead of a 2-tuple, and there should be a generic
  // data version create/read/update/delete method. As there should be for
  // every object in the database.
  markDataVersionsRead(wfModuleId, data_versions) {
    return this._patch(`/api/wfmodules/${wfModuleId}/dataversion/read`, { versions: data_versions })
  }

  postParamEvent(paramId, data) {
    return this._post(`/api/parameters/${paramId}/event`, data)
  }
}

// Singleton API object for global use
const api = new WorkbenchAPI();
export default () => { return api; }
