// Wraps all API calls. Useful both to centralize and abstract these calls,
// also for dependency injection for testing

import {csrfToken} from './utils'

const apiHeaders = {
  'Accept': 'application/json',
  'Content-Type': 'application/json',
  'X-CSRFToken': csrfToken
}

// All API calls which fetch data return a promise which returns JSON
export default class WorkbenchAPI {
  constructor (websocket) {
    this.websocket = websocket
  }

  // We send at most one data-modification request at a time, to avoid races.
  // this._serializer always resolves to the last-returned fetch result.
  _serializer = Promise.resolve(null)

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

    return this._serializer = this._serializer.catch(() => null)
      .then(() => fetch(url, realOptions))
      .then(res => {
        if (!res.ok) {
          throw new RangeError(`Server responded with non-200 status code ${res.status}`)
        }
        if (res.status === 204) {
          return null // No content
        }
        if (res.headers.get('content-type') && res.headers.get('content-type').toLowerCase().indexOf('application/json') === -1) {
          throw new TypeError("Server response is not JSON", res)
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
    return this._submit('PATCH', url, body, options)
  }

  _put(url, body, options) {
    return this._submit('PUT', url, body, options)
  }

  _post(url, body, options) {
    return this._submit('POST', url, body, options)
  }

  _delete(url, options) {
    return this._submit('delete', url, null, { body: '' })
  }

  listWorkflows() {
    return this._fetch('/api/workflows')
  }

  newWorkflow() {
    return this._post('/api/workflows', {})
  }

  deleteWorkflow(workflowId) {
    return this._delete(`/api/workflows/${workflowId}`)
  }

  getAcl (workflowId) {
    return this._fetch(`/api/workflows/${workflowId}/acl`)
      .then(json => {
        // rename can_edit => canEdit
        return json.map(({ email, can_edit }) => ({ email, canEdit: can_edit }))
      })
  }

  updateAclEntry (workflowId, email, canEdit) {
    return this._put(`/api/workflows/${workflowId}/acl/${encodeURIComponent(email)}`, { can_edit: canEdit })
  }

  deleteAclEntry (workflowId, email) {
    return this._delete(`/api/workflows/${workflowId}/acl/${encodeURIComponent(email)}`)
  }

  setTabOrder (tabIds) {
    return this.websocket.callServerHandler('workflow.set_tab_order', {
      tabIds
    })
  }

  reorderWfModules (tabId, wfModuleIds) {
    return this.websocket.callServerHandler('tab.reorder_modules', {
      tabId,
      wfModuleIds
    })
  }

  addModule (tabId, moduleId, index, values={}) {
    return this.websocket.callServerHandler('tab.add_module', {
      tabId,
      moduleId,
      position: index,
      paramValues: values
    })
  }

  createTab (name) {
    return this.websocket.callServerHandler('tab.create', { name })
  }

  deleteModule(wfModuleId) {
    return this.websocket.callServerHandler('wf_module.delete', {
      wfModuleId
    })
  }

  deleteTab (tabId) {
    return this.websocket.callServerHandler('tab.delete', {
      tabId
    })
  }

  setWorkflowPublic(workflowId, isPublic) {
    return this._post(`/api/workflows/${workflowId}`, { 'public': isPublic })
  }

  setWfModuleParams (wfModuleId, values) {
    return this.websocket.callServerHandler('wf_module.set_params', {
      wfModuleId,
      values
    })
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

  valueCounts(wfModuleId, column) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/value-counts?column=${encodeURIComponent(column)}`)
      .catch(err => {
        if (err instanceof RangeError) {
          return { values: {} }
        } else {
          throw err
        }
      })
      .then(json => json.values)
  }

  output(wfModuleId) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/output`)
  }

  getTile(wfModuleId, deltaId, tileRow, tileColumn) {
    return this._fetch(`/api/wfmodules/${wfModuleId}/v${deltaId}/r${tileRow}/c${tileColumn}.json`)
  }

  setTabName (tabId, name) {
    return this.websocket.callServerHandler('tab.set_name', {
      tabId,
      name
    })
  }

  setWfModuleVersion (wfModuleId, version) {
    return this.websocket.callServerHandler('wf_module.set_stored_data_version', {
      wfModuleId,
      version
    })
  }

  setWfModuleNotes (wfModuleId, notes) {
    return this.websocket.callServerHandler('wf_module.set_notes', {
      wfModuleId,
      notes
    })
  }

  setWfModuleCollapsed (wfModuleId, isCollapsed) {
    return this.websocket.callServerHandler('wf_module.set_collapsed', {
      wfModuleId,
      isCollapsed
    })
  }

  setWorkflowName (name) {
    return this.websocket.callServerHandler('workflow.set_name', { name })
  }

  /**
   * Tell the server which module to tell the client to open on next page load.
   *
   * This is a courtesy message: we really don't care if there are races or
   * other shenanigans that prevent the selection from happening, as it doesn't
   * affect any data.
   */
  setSelectedWfModule (wfModuleId ) {
    return this.websocket.callServerHandler('workflow.set_selected_wf_module', {
      wfModuleId
    })
  }

  /**
   * Tell the server which module to tell the client to open on next page load.
   *
   * This is a courtesy message: we really don't care if there are races or
   * other shenanigans that prevent the selection from happening, as it doesn't
   * affect any data.
   */
  setSelectedTab (tabId) {
    return this.websocket.callServerHandler('workflow.set_selected_tab', {
      tabId
    })
  }

  updateWfModule(wfModuleId, params) {
    // TODO websocket-ize
    return this._patch(`/api/wfmodules/${wfModuleId}`, params)
  }

  undo(workflowId) {
    return this.websocket.callServerHandler('workflow.undo', {})
  }

  redo(workflowId) {
    return this.websocket.callServerHandler('workflow.redo', {})
  }

  duplicateWorkflow(workflowId) {
    return this._post(`/api/workflows/${workflowId}/duplicate`, null)
  }

  deleteWfModuleNotifications(wfModuleId) {
    // TODO websocket-ize
    return this._delete(`/api/wfmodules/${wfModuleId}/notifications`)
  }

  importModuleFromGitHub(url) {
    return this._post('/api/importfromgithub/', { url })
      .then(json => {
        // Turn OK {'error': 'no can do'} into a Promise Error
        if (json.error) throw new Error(json.error)
        return json
      })
  }

  requestFetch (wfModuleId) {
    return this.websocket.callServerHandler('wf_module.fetch', {
      wfModuleId
    })
  }

  /**
   * Return a String access token, or null.
   *
   * On auth error (or any other error), warn on console and return null.
   */
  createOauthAccessToken (wfModuleId, param) {
    return this.websocket.callServerHandler('wf_module.generate_secret_access_token', {
      wfModuleId,
      param
    })
      .then(
        (({ token }) => token), // token may be null
        (err) => {
          console.warn('Server did not generate OAuth token:', err)
          return null
        }
      )
  }

  paramOauthDisconnect(paramId) {
    return this._delete(`/api/parameters/${paramId}/oauth_authorize`)
  }
}
