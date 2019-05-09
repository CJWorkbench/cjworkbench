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

  _callExpectingNull (...args) {
    return this.websocket.callServerHandler(...args)
      .catch(err => {
        if (err.serverError) {
          console.error('Message from server: ', err.serverError, err)
        } else {
          console.error(err)
        }
      })
  }

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

  setTabOrder (tabSlugs) {
    return this._callExpectingNull('workflow.set_tab_order', {
      tabSlugs
    })
  }

  reorderWfModules (tabSlug, wfModuleIds) {
    return this._callExpectingNull('tab.reorder_modules', {
      tabSlug,
      wfModuleIds
    })
  }

  addModule (tabSlug, moduleIdName, index, values={}) {
    return this._callExpectingNull('tab.add_module', {
      tabSlug,
      moduleIdName,
      position: index,
      paramValues: values
    })
  }

  createTab (slug, name) {
    return this._callExpectingNull('tab.create', { slug, name })
  }

  /**
   * Ask server to duplicate the tab `tabSlug`, creating new `slug` and `name`.
   */
  duplicateTab (tabSlug, slug, name) {
    return this._callExpectingNull('tab.duplicate', { tabSlug, slug, name })
  }

  deleteModule(wfModuleId) {
    return this._callExpectingNull('wf_module.delete', {
      wfModuleId
    })
  }

  deleteTab (tabSlug) {
    return this._callExpectingNull('tab.delete', {
      tabSlug
    })
  }

  setWorkflowPublic(workflowId, isPublic) {
    return this._post(`/api/workflows/${workflowId}`, { 'public': isPublic })
  }

  setWfModuleParams (wfModuleId, values) {
    return this._callExpectingNull('wf_module.set_params', {
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

  setTabName (tabSlug, name) {
    return this._callExpectingNull('tab.set_name', {
      tabSlug,
      name
    })
  }

  setWfModuleVersion (wfModuleId, version) {
    return this._callExpectingNull('wf_module.set_stored_data_version', {
      wfModuleId,
      version
    })
  }

  setWfModuleNotes (wfModuleId, notes) {
    return this._callExpectingNull('wf_module.set_notes', {
      wfModuleId,
      notes
    })
  }

  setWfModuleCollapsed (wfModuleId, isCollapsed) {
    return this._callExpectingNull('wf_module.set_collapsed', {
      wfModuleId,
      isCollapsed
    })
  }

  setWorkflowName (name) {
    return this._callExpectingNull('workflow.set_name', { name })
  }

  /**
   * Tell the server which module to tell the client to open on next page load.
   *
   * This is a courtesy message: we really don't care if there are races or
   * other shenanigans that prevent the selection from happening, as it doesn't
   * affect any data.
   */
  setSelectedWfModule (wfModuleId ) {
    return this._callExpectingNull('workflow.set_position', {
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
  setSelectedTab (tabSlug) {
    return this._callExpectingNull('workflow.set_selected_tab', {
      tabSlug
    })
  }

  updateWfModule(wfModuleId, params) {
    // TODO websocket-ize
    return this._patch(`/api/wfmodules/${wfModuleId}`, params)
  }

  undo(workflowId) {
    return this._callExpectingNull('workflow.undo', {})
  }

  redo(workflowId) {
    return this._callExpectingNull('workflow.redo', {})
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
    return this._callExpectingNull('wf_module.fetch', {
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

  /**
   * Open a popup, and close when the auth popup completes successfully.
   *
   * Yup, this is really strange. There's no return value here; watch the
   * state to see success/failure.
   */
  startCreateSecret (workflowId, wfModuleId, param) {
    /**
     * Return true if popup is pointed at an oauth-success page.
     */
    const isOauthFinished = (popup) => {
      try {
        if (!/^\/oauth\/?/.test(popup.location.pathname)) {
          // We're at the wrong URL.
          return false
        }
      } catch (_) {
        // We're cross-origin. That's certainly the wrong URL.
        return false
      }

      return popup.document.querySelector('p.success')

      // If p.success is not present, the server has not indicated success.
      // That means one of the following:
      // 1) error message
      // 2) request has not completed
      // ... in either case, oauth is not finished
    }

    const popup = window.open(
      `/oauth/create-secret/${workflowId}/${wfModuleId}/${param}/`,
      'workbench-oauth',
      'height=500,width=400'
    )
    if (!popup) {
      console.error('Could not open auth popup')
      return
    }

    // Watch the popup incessantly, and close it when the user is done with it
    const interval = window.setInterval(() => {
      if (!popup || popup.closed || isOauthFinished(popup)) {
        if (popup && !popup.closed) popup.close()
        window.clearInterval(interval);
      }
    }, 100)
  }

  deleteSecret (wfModuleId, param) {
    return this._callExpectingNull('wf_module.delete_secret', {
      wfModuleId,
      param
    })
  }
}
