// Wraps all API calls. Useful both to centralize and abstract these calls,
// also for dependency injection for testing

import { csrfToken } from './utils'

// All API calls which fetch data return a promise which returns JSON
class WorkbenchAPI {

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
}

// Singleton API object for global use
const api = new WorkbenchAPI();
export default () => { return api; }
