/* globals fetch */
import { csrfToken } from './utils'

const apiHeaders = {
  Accept: 'application/json',
  'Content-Type': 'application/json',
  'X-CSRFToken': csrfToken
}

const ResetSerializer = () => null

// All API calls which fetch data return a promise which returns JSON
export default class WorkbenchAPI {
  constructor (websocket) {
    if (websocket !== null) {
      this.websocket = websocket
      this.workflowIdOrSecretId = websocket.workflowIdOrSecretId
    }
  }

  // We send at most one data-modification request at a time, to avoid races.
  // this._serializer resolves to `null` and completes when the last requested
  // fetch is completed.
  _serializer = Promise.resolve(null)

  /**
   * Send a message to the server; wait for a null response.
   *
   * @async
   * @throws ErrorResponse if the server rejects the request or there's a
   *                       network error. The caller is responsible for
   *                       handling this error.
   */
  _callExpectingNull (handler, ...args) {
    return this.websocket.callServerHandler(handler, ...args)
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
   * * DOMException if there's a network error or malformed response.
   */
  _fetch (url, options) {
    const realOptions = Object.assign({ credentials: 'include' }, options || {})

    const ret = this._serializer
      // fetch() throws:
      // RangeError (status < 200 || status >= 600)
      // TypeError (invalid statusText)
      // "AbortError" DOMException (aborted)
      // Other DOMExceptions (network error)
      .then(() => fetch(url, realOptions))
      .then(res => {
        if (!res.ok) {
          throw new RangeError(
            `Server responded with non-200 status code ${res.status}`
          )
        }
        if (res.status === 204) {
          return null // No content
        }
        if (
          res.headers.get('content-type') &&
          res.headers
            .get('content-type')
            .toLowerCase()
            .indexOf('application/json') === -1
        ) {
          throw new TypeError('Server response is not JSON', res)
        }
        // throws:
        // SyntaxError (not valid JSON)
        // Other DOMExceptions
        return res.json()
      })

    this._serializer = ret.then(ResetSerializer, ResetSerializer)
    return ret
  }

  _submit (method, url, body, options) {
    const realOptions = Object.assign(
      { method: method, headers: apiHeaders },
      { body: JSON.stringify(body) },
      options || {}
    )
    return this._fetch(url, realOptions)
  }

  _put (url, body, options) {
    return this._submit('PUT', url, body, options)
  }

  _post (url, body, options) {
    return this._submit('POST', url, body, options)
  }

  _delete (url, options) {
    return this._submit('delete', url, null, { body: '' })
  }

  deleteWorkflow (workflowId) {
    return this._delete(`/api/workflows/${workflowId}`)
  }

  updateAclEntry (workflowId, email, role) {
    return this._put(
      `/workflows/${workflowId}/acl/${encodeURIComponent(email)}`,
      { role }
    )
  }

  deleteAclEntry (workflowId, email) {
    return this._delete(
      `/workflows/${workflowId}/acl/${encodeURIComponent(email)}`
    )
  }

  setTabOrder (tabSlugs) {
    return this._callExpectingNull('workflow.set_tab_order', {
      tabSlugs
    })
  }

  reorderSteps ({ mutationId, tabSlug, slugs }) {
    return this._callExpectingNull('tab.reorder_steps', {
      mutationId,
      tabSlug,
      slugs
    })
  }

  addStep (tabSlug, slug, moduleIdName, index, values = {}) {
    return this._callExpectingNull('tab.add_module', {
      tabSlug,
      slug,
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

  deleteStep (stepId) {
    return this._callExpectingNull('step.delete', { stepId })
  }

  deleteTab (tabSlug) {
    return this._callExpectingNull('tab.delete', { tabSlug })
  }

  addBlock (args) {
    return this._callExpectingNull('report.add_block', args)
  }

  deleteBlock (args) {
    return this._callExpectingNull('report.delete_block', args)
  }

  reorderBlocks (args) {
    return this._callExpectingNull('report.reorder_blocks', args)
  }

  setBlockMarkdown (args) {
    return this._callExpectingNull('report.set_block_markdown', args)
  }

  setWorkflowPublicAccess (workflowId, isPublic, hasSecret) {
    return this._put(
      `/workflows/${workflowId}/acl`,
      { public: isPublic, has_secret: hasSecret }
    )
  }

  trySetStepAutofetch (stepSlug, isAutofetch, fetchInterval) {
    return this.websocket.callServerHandler('step.try_set_autofetch', {
      stepSlug,
      isAutofetch,
      fetchInterval
    })
  }

  setStepNotifications (stepId, notifications) {
    return this._callExpectingNull('step.set_notifications', {
      stepId,
      notifications
    })
  }

  setStepParams (stepId, values) {
    return this._callExpectingNull('step.set_params', {
      stepId,
      values
    })
  }

  getStepResultTableSlice (stepSlug, deltaId, startRow, endRow) {
    const path = `/workflows/${this.workflowIdOrSecretId}/steps/${stepSlug}/delta-${deltaId}/result-table-slice.json`

    const params = new URLSearchParams()
    if (startRow) {
      params.set('startrow', String(startRow))
    }
    if (endRow) {
      params.set('endrow', String(endRow))
    }
    const queryString = params.toString()

    const url = path + (queryString ? ('?' + queryString) : '')

    return this._fetch(url)
  }

  stepResultColumnValueCounts (stepSlug, deltaId, column) {
    return this._fetch(
      `/workflows/${this.workflowIdOrSecretId}/steps/${stepSlug}/delta-${deltaId}/result-column-value-counts.json?column=${encodeURIComponent(column)}`
    )
      .catch(err => {
        if (err instanceof RangeError) {
          return { values: {} }
        } else {
          throw err
        }
      })
      .then(json => json.values)
  }

  getTile (stepId, deltaId, tileRow, tileColumn) {
    return this._fetch(
      `/api/wfmodules/${stepId}/v${deltaId}/r${tileRow}/c${tileColumn}.json`
    )
  }

  setTabName (tabSlug, name) {
    return this._callExpectingNull('tab.set_name', {
      tabSlug,
      name
    })
  }

  setStepVersion (stepId, version) {
    return this._callExpectingNull('step.set_stored_data_version', {
      stepId,
      version
    })
  }

  setStepNotes (stepId, notes) {
    return this._callExpectingNull('step.set_notes', {
      stepId,
      notes
    })
  }

  setStepCollapsed (stepId, isCollapsed) {
    return this._callExpectingNull('step.set_collapsed', {
      stepId,
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
  setSelectedStep (stepId) {
    return this._callExpectingNull('workflow.set_position', {
      stepId
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

  undo () {
    return this._callExpectingNull('workflow.undo', {})
  }

  redo () {
    return this._callExpectingNull('workflow.redo', {})
  }

  duplicateWorkflow (workflowIdOrSecretId) {
    return this._post(`/workflows/${workflowIdOrSecretId}/duplicate`, null)
  }

  clearStepUnseenNotifications (stepId) {
    return this._callExpectingNull('step.clear_unseen_notifications', {
      stepId
    })
  }

  importModuleFromGitHub (url) {
    return this._post('/api/importfromgithub/', { url }).then(json => {
      // Turn OK {'error': 'no can do'} into a Promise Error
      if (json.error) throw new Error(json.error)
      return json
    })
  }

  requestFetch (stepId) {
    return this._callExpectingNull('step.fetch', {
      stepId
    })
  }

  /**
   * Return a String access token, or null.
   *
   * On auth error (or any other error), warn on console and return null.
   */
  createOauthAccessToken (stepId, param) {
    return this.websocket
      .callServerHandler('step.generate_secret_access_token', {
        stepId,
        param
      })
      .then(
        ({ token }) => token, // token may be null
        err => {
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
  startCreateSecret (stepId, param) {
    /**
     * Return true if popup is pointed at an oauth-success page.
     */
    const isOauthFinished = popup => {
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
      `/oauth/create-secret/${this.workflowIdOrSecretId}/${stepId}/${param}/`,
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
        window.clearInterval(interval)
      }
    }, 100)
  }

  deleteSecret (stepId, param) {
    return this._callExpectingNull('step.delete_secret', {
      stepId,
      param
    })
  }

  setSecret (stepId, param, secret) {
    return this._callExpectingNull('step.set_secret', {
      stepId,
      param,
      secret
    })
  }

  async _getUploadManagerPromise () {
    if (!this._uploadManagerPromise) {
      const { default: UploadManager } = await import(
        /* webpackChunkName: "upload-manager" */ './UploadManager'
      )
      this._uploadManagerPromise = new UploadManager(this.websocket)
    }
    return this._uploadManagerPromise
  }

  async uploadFile (stepSlug, file, onProgress) {
    const uploadManager = await this._getUploadManagerPromise()
    return uploadManager.upload(stepSlug, file, onProgress)
  }

  async cancelFileUpload (stepSlug) {
    const uploadManager = await this._getUploadManagerPromise()
    return uploadManager.cancel(stepSlug)
  }

  async getStepFileUploadApiToken (stepSlug) {
    return this.websocket
      .callServerHandler('step.get_file_upload_api_token', { stepSlug })
      .then(({ apiToken }) => apiToken)
  }

  async resetStepFileUploadApiToken (stepSlug) {
    return this.websocket
      .callServerHandler('step.reset_file_upload_api_token', { stepSlug })
      .then(({ apiToken }) => apiToken)
  }

  async clearStepFileUploadApiToken (stepSlug) {
    return this._callExpectingNull('step.clear_file_upload_api_token', {
      stepSlug
    })
  }

  /**
   * Construct { checkoutSession, apiKey } pair, for @stripe/stripe-js calls.
   */
  async createStripeCheckoutSession (stripePriceId) {
    return this._post('/stripe/create-checkout-session', { stripePriceId })
  }

  /**
   * Construct { billingPortalSession }, for client-side redirects.
   */
  async createStripeBillingPortalSession () {
    return this._post('/stripe/create-billing-portal-session')
  }
}
