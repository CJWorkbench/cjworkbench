/* global describe, it, expect */
import * as wfr from './workflow-reducer'
import { mockStore, tick } from './test-utils'

describe('Reducer actions', () => {
  const testModules = {
    '1': {
      id: 1,
      id_name: 'module1'
    },
    '2': {
      id: 2,
      id_name: 'module2'
    }
  }

  const testWfModules = {
    '10': {
      id: 10,
      tab_slug: 'tab-91',
      params: { 'data': 'Some Data', 'version_select': null },
      versions: {
        selected: "2018-02-21T03:09:20.214054Z",
        versions: [
          ["2018-02-21T03:09:20.214054Z", true],
          ["2018-02-21T03:09:15.214054Z", false],
          ["2018-02-21T03:09:10.214054Z", false]
        ]
      },
      has_unseen_notification: true
    },
    '20': {
      id: 20,
      tab_slug: 'tab-91'
    },
    '30': {
      id: 30,
      tab_slug: 'tab-91'
    }
  }

  const testTabs = {
    'tab-91': {
      slug: 'tab-91',
      wf_module_ids: [ 10, 20, 30 ],
      selected_wf_module_position: 1
    }
  }

  // Stripped down workflow object, only what we need for testing actions
  const testWorkflow = {
    id: 999,
    tab_slugs: [ 'tab-91' ]
  }

  // test state has second module selected
  const testState = {
    workflow: testWorkflow,
    tabs: testTabs,
    wfModules: testWfModules,
    modules: testModules,
  }

  it('sets the workflow name', async () => {
    const api = {
      setWorkflowName: jest.fn().mockImplementation(() => Promise.resolve(null))
    }
    const store = mockStore({ workflow: { a: 1, name: 'A' }, b: 2 }, api)

    await store.dispatch(wfr.setWorkflowNameAction('B'))
    expect(api.setWorkflowName).toHaveBeenCalledWith('B')
    expect(store.getState()).toEqual({
      workflow: { a: 1, name: 'B' },
      b: 2
    })
  })

  it('returns the state if we feed garbage to the reducer', () => {
    const initialState = {'x': 'y'}
    const state = wfr.workflowReducer(initialState, {
      type: 'An ill-advised request',
      payload: {
        blob: 'malware.exe'
      }
    })
    expect(state).toBe(initialState)
  })

  // ADD_MODULE
  it('adds a module by index', async () => {
    const api = {
      addModule: jest.fn(() => Promise.resolve(null))
    }

    const store = mockStore({
      workflow: {
        tab_slugs: [ 'tab-1' ]
      },
      tabs: {
        'tab-1': {
          wf_module_ids: [2, 3],
          selected_wf_module_position: 1
        }
      },
      wfModules: {
        2: {},
        3: {}
      },
      modules: {
        'module2': {}
      }
    }, api)

    await store.dispatch(wfr.addModuleAction('module2', { tabSlug: 'tab-1', index: 0 }, { x: 'y' }))

    expect(api.addModule).toHaveBeenCalledWith('tab-1', 'module2', 0, { x: 'y' })
    const state = store.getState()
    expect(state.tabs['tab-1'].selected_wf_module_position).toEqual(0)
    expect(state.tabs['tab-1'].wf_module_ids).toEqual(['nonce-module2-0', 2, 3])
  })

  it('adds a module before another', async () => {
    const api = {
      addModule: jest.fn(() => Promise.resolve(null))
    }

    const store = mockStore({
      workflow: {
        tab_slugs: [ 'tab-1' ]
      },
      tabs: {
        'tab-1': {
          wf_module_ids: [2, 3],
          selected_wf_module_position: 1
        }
      },
      wfModules: {
        2: {},
        3: { tab_slug: 'tab-1' }
      },
      modules: {
        'module2': {}
      }
    }, api)

    await store.dispatch(wfr.addModuleAction('mod', { beforeWfModuleId: 3 }, { x: 'y' }))
    expect(api.addModule).toHaveBeenCalledWith('tab-1', 'mod', 1, { x: 'y' })
  })

  it('adds a module after another', async () => {
    const api = {
      addModule: jest.fn(() => Promise.resolve(null))
    }

    const store = mockStore({
      workflow: {
        tab_slugs: [ 'tab-1' ]
      },
      tabs: {
        'tab-1': {
          wf_module_ids: [2, 3],
          selected_wf_module_position: 1
        }
      },
      wfModules: {
        2: { tab_slug: 'tab-1' },
        3: {}
      },
      modules: {
        'module2': {}
      }
    }, api)

    await store.dispatch(wfr.addModuleAction('mod', { afterWfModuleId: 2 }, { x: 'y' }))
    expect(api.addModule).toHaveBeenCalledWith('tab-1', 'mod', 1, { x: 'y' })
  })

  it('deletes a module', async () => {
    const api = {
      deleteModule: jest.fn().mockImplementation(_ => Promise.resolve(null))
    }
    const store = mockStore(testState, api)
    await store.dispatch(wfr.deleteModuleAction(20))

    expect(api.deleteModule).toHaveBeenCalledWith(20)
    const state = store.getState()
    expect(state.tabs['tab-91'].wf_module_ids).toEqual([ 10, 30 ])
    expect(state.wfModules['20']).not.toBeDefined()
  })

  it('sets the selected module to a module in state', async () => {
    const api = {
      setSelectedWfModule: jest.fn().mockImplementation(_ => Promise.resolve(null))
    }
    const store = mockStore(testState, api)
    await store.dispatch(wfr.setSelectedWfModuleAction(20))

    expect(api.setSelectedWfModule).toHaveBeenCalledWith(20)
    const { workflow, tabs } = store.getState()
    expect(workflow.selected_tab_position).toEqual(0)
    expect(tabs['tab-91'].selected_wf_module_position).toEqual(1)
  })

  it('sets a wfModule notes', async () => {
    const api = {
      setWfModuleNotes: jest.fn().mockImplementation(() => Promise.resolve(null))
    }
    const store = mockStore({
      wfModules: {
        1: { x: 'a', notes: 'foo' },
        2: { x: 'b', notes: 'bar' }
      }
    }, api)

    await store.dispatch(wfr.setWfModuleNotesAction(2, 'baz'))

    expect(api.setWfModuleNotes).toHaveBeenCalledWith(2, 'baz')
    const state = store.getState()
    expect(state).toEqual({
      wfModules: {
        1: { x: 'a', notes: 'foo' },
        2: { x: 'b', notes: 'baz' }
      }
    })
  })

  it('updates the workflow module with the specified data', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'UPDATE_WF_MODULE_PENDING',
      payload: {
        wfModuleId: 20,
        data: {
          notifications: true
        }
      }
    })
    expect(state.wfModules['20'].notifications).toBe(true)
  })

  it('does nothing if we update a nonexistent wfmodule', async () => {
    const api = { updateWfModule: jest.fn() }
    const store = mockStore(testState, api)
    await store.dispatch(wfr.updateWfModuleAction(40, { notifications: false }))

    expect(api.updateWfModule).not.toHaveBeenCalled()
    expect(store.getState()).toEqual(testState)
  })

  it('reorders modules', async () => {
    const api = {
      reorderWfModules: jest.fn().mockImplementation(() => Promise.resolve(null))
    }
    const store = mockStore({
      workflow: {
        tab_slugs: 'tab-1'
      },
      tabs: {
        'tab-1': {
          wf_module_ids: [ 2, 4, 6 ],
          selected_wf_module_position: 2
        }
      }
    }, api)
    await store.dispatch(wfr.moveModuleAction('tab-1', 2, 0))

    // Change happens synchronously. No need to even await the promise :)
    expect(api.reorderWfModules).toHaveBeenCalledWith('tab-1', [ 6, 2, 4])
    expect(store.getState().tabs['tab-1'].wf_module_ids).toEqual([ 6, 2, 4 ])
    expect(store.getState().tabs['tab-1'].selected_wf_module_position).toEqual(0)
  })

  it('applies delta to a Workflow', () => {
    const state = wfr.workflowReducer(testState, wfr.applyDeltaAction({
      updateWorkflow: { foo: 'bar' }
    }))
    expect(state.workflow.wf_modules).toBe(testState.workflow.wf_modules) // old property
    expect(state.workflow.foo).toEqual('bar') // new property
  })

  it('applies delta to a WfModule', () => {
    const state = wfr.workflowReducer(testState, wfr.applyDeltaAction({
      updateWfModules: { '10': { foo: 'bar' } }
    }))
    expect(state.wfModules['10'].foo).toEqual('bar') // new property
    expect(state.wfModules['10'].params).toBe(testState.wfModules['10'].params) // old property
    expect(state.wfModules['20']).toBe(testState.wfModules['20']) // old WfModule
    expect(state.wfModules).not.toBe(testState.wfModules) // immutable
  })

  it('applies delta to clearing a WfModule', () => {
    const state = wfr.workflowReducer(testState, wfr.applyDeltaAction({
      updateWorkflow: { wf_modules: [ 10, 30 ] },
      clearWfModuleIds: [ 20 ]
    }))
    expect(state.wfModules).not.toBe(testState.wfModules) // immutable
    expect(state.wfModules['10']).toBe(testState.wfModules['10']) // leave uncleared modules unchanged
    expect(state.wfModules['20']).not.toBeDefined()
  })

  it('applies delta to a Tab', () => {
    const state = wfr.workflowReducer(testState, wfr.applyDeltaAction({
      updateTabs: {
        'tab-91': { foo: 'bar', selected_wf_module_position: 0 },
        'tab-92': { foo: 'baz' }
      }
    }))
    expect(state.tabs['tab-91'].foo).toEqual('bar') // new property
    expect(state.tabs['tab-92'].foo).toEqual('baz')
    expect(state.tabs['tab-91'].wf_module_ids).toEqual([ 10, 20, 30 ]) // old property
    expect(state.tabs['tab-91'].selected_wf_module_position).toEqual(1) // immutable
  })

  it('applies delta to clearing a Tab', () => {
    const state = wfr.workflowReducer(testState, wfr.applyDeltaAction({
      clearTabSlugs: [ 'tab-91' ],
    }))
    expect(state.tabs).toEqual({})
  })

  it('moves a tab from pendingTabs to tabs', () => {
    // This "pendingTabs" thing is half-baked. Really, we're trying to simulate
    // a "command queue" on the client  -- that is, commands the user sees that
    // haven't been applied on the server yet. TODO nix pendingTabs when we
    // have a sane way of doing that.
    const oldTab = { slug: 'tab-1', name: 'Old' }
    const newTab = { slug: 'tab-NEW', name: 'New', wf_module_ids: [], selected_wf_module_position: null }

    const state = wfr.workflowReducer({
      workflow: {
        tab_slugs: [ 'tab-1', 'tab-NEW' ],
      },
      tabs: { 'tab-1': oldTab },
      pendingTabs: { 'tab-NEW': newTab }
    }, wfr.applyDeltaAction({
      updateTabs: { 'tab-NEW': newTab }
    }))

    expect(state.tabs).toEqual({
      'tab-1': oldTab,
      'tab-NEW': newTab
    })

    expect(state.pendingTabs).toEqual({})
  })

  it('sets the module collapse state', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'SET_WF_MODULE_COLLAPSED_PENDING',
      payload: {
        wfModuleId: 20,
        isCollapsed: true
      }
    })
    expect(state.wfModules['20'].is_collapsed).toBe(true)
  })

  it('should setWfModuleParams', async () => {
    const api = {
      setWfModuleParams: jest.fn(() => Promise.resolve(null))
    }

    const store = mockStore({
      wfModules: {
        10: {
          params: {
            'a': 'x',
            'b': 'y'
          }
        }
      }
    }, api)
    const done = store.dispatch(wfr.setWfModuleParamsAction(10, { 'a': 'z' }))

    // should set value immediately
    expect(store.getState().wfModules['10'].params).toEqual({ 'a': 'z', 'b': 'y' })

    // should send HTTP request
    await done
    expect(api.setWfModuleParams).toHaveBeenCalledWith(10, { 'a': 'z' })
  })

  it('requests fetch in maybeRequestWfModuleFetchAction', async () => {
    const api = {
      requestFetch: jest.fn().mockImplementation(_ => Promise.resolve(null))
    }
    const store = mockStore({
      wfModules: {
        10: {
          module: 'mod'
        }
      },
      modules: {
        mod: {
          param_fields: [
            { idName: 'foo' },
            { idName: 'version_select' }
          ]
        }
      }
    }, api)
    const done = store.dispatch(wfr.maybeRequestWfModuleFetchAction(10))

    // should set nClientRequests immediately.
    expect(store.getState().wfModules['10'].nClientRequests).toEqual(1)
    expect(api.requestFetch).toHaveBeenCalledWith(10)

    await done
    expect(store.getState().wfModules['10'].nClientRequests).toEqual(0)
  })

  it('sets the data version', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'SET_DATA_VERSION_PENDING',
      payload: {
        wfModuleId: 10,
        selectedVersion: "2018-02-21T03:09:10.214054Z"
      }
    })
    expect(state.wfModules['10'].versions.selected).toBe("2018-02-21T03:09:10.214054Z")
  })

  it('clears the notification count', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'CLEAR_NOTIFICATIONS_PENDING',
      payload: {
        wfModuleId: 10
      }
    })
    expect(state.wfModules['10'].has_unseen_notification).toBe(false)
  })
})
