/* global describe, it, expect */
jest.mock('./WorkbenchAPI')
import * as wfr from './workflow-reducer'
import WorkbenchAPI from './WorkbenchAPI'
import { tick } from './test-utils'

const mockStore = wfr.mockStore

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
      parameter_vals: [
        {
          id: 1,
          parameter_spec: {
            id_name: 'data',
          },
          value: 'Some Data'
        },
        {
          // maybeRequestWfModuleFetchAction() requires version_select.
          id: 2,
          parameter_spec: {
            id_name: 'version_select'
          },
          value: null
        }
      ],
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
      id: 20
    },
    '30': {
      id: 30
    }
  }

  // Stripped down workflow object, only what we need for testing actions
  const testWorkflow = {
    id: 999,
    wf_modules: [ 10, 20, 30 ]
  }

  // test state has second module selected
  const testState = {
    workflow: testWorkflow,
    wfModules: testWfModules,
    modules: testModules,
    selected_wf_module: 1
  }

  beforeEach(() => {
    WorkbenchAPI.getModules.mockReset()
    WorkbenchAPI.addModule.mockReset()
    WorkbenchAPI.deleteModule.mockReset()
    WorkbenchAPI.setSelectedWfModule.mockReset()
    WorkbenchAPI.updateWfModule.mockReset()
    WorkbenchAPI.onParamChanged.mockReset()
    WorkbenchAPI.markDataVersionsRead.mockReset()
    WorkbenchAPI.reorderWfModules.mockReset()
    WorkbenchAPI.requestFetch.mockReset()
  })

  it('Returns the state if we feed garbage to the reducer', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'An ill-advised request',
      payload: {
        blob: 'malware.exe'
      }
    });
    expect(state).toBe(testState);
  });

  // RELOAD_WORKFLOW
   it('Reloads the workflow', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'RELOAD_WORKFLOW_FULFILLED',
      payload: { workflow: testWorkflow, wfModules: testWfModules }
    });
    expect(state.workflow).toEqual(testWorkflow)
  });

  it('does not overwrite is_collapsed when reloading workflow', () => {
    // https://www.pivotaltracker.com/story/show/158620575
    const wfModules1 = {
      10: { ...testWfModules['10'] },
      20: { ...testWfModules['20'], is_collapsed: false },
      30: { ...testWfModules['30'], is_collapsed: true }
    }

    const wfModules2 = {
      10: { ...wfModules1['10'] },
      20: { ...wfModules1['20'], is_collapsed: true },
      30: { ...wfModules1['30'], is_collapsed: false }
    }

    const state = wfr.workflowReducer({ workflow: testWorkflow, wfModules: wfModules1 }, {
      type: 'RELOAD_WORKFLOW_FULFILLED',
      payload: { workflow: testWorkflow, wfModules: wfModules2 }
    })

    expect(state.wfModules['20'].is_collapsed).toBe(false)
    expect(state.wfModules['30'].is_collapsed).toBe(true)
  })

   // LOAD_MODULES
  it('loadModules', async () => {
    const moduleArray = [
      {
        "id":1,
        "name":"Chart",
        "category":"Visualize",
        "description":"Create line, column and scatter plot charts.",
        "icon":"chart"
      },
      {
        "id":2,
        "name":"Load from Facebork",
        "category":"Add data",
        "description":"Import from your favorite snowshall media",
        "icon":"url"
      },
      {
        "id":3,
        "name":"Load from Enigma",
        "category":"Add data",
        "description":"Connect a dataset from Enigma's collection via URL.",
        "icon":"url"
      }
    ]

    // State stores a dict keyed by ID. API returns an Array.
    WorkbenchAPI.getModules.mockImplementation(_ => Promise.resolve(moduleArray))

    const store = mockStore({ ...testState, modules: {} })
    await store.dispatch(wfr.loadModulesAction())

    expect(WorkbenchAPI.getModules).toHaveBeenCalled()
    expect(store.getState().modules).toEqual({
      "1": moduleArray[0],
      "2": moduleArray[1],
      "3": moduleArray[2]
    })
  })

  // ADD_MODULE
  it('adds a module', async () => {
    WorkbenchAPI.addModule.mockImplementation(_ => Promise.resolve({
      index: 2,
      wfModule: {
        id: 40,
        foo: 'bar'
      }
    }))

    const store = mockStore(testState)
    await store.dispatch(wfr.addModuleAction(1, 2, { x: 'y' }))

    expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(999, 1, 2, { x: 'y' })
    const state = store.getState()
    expect(state.workflow.wf_modules).toEqual([ 10, 20, 40, 30 ])
    expect(state.selected_wf_module).toEqual(2)
  })

  it('adds a module by idName', async () => {
    WorkbenchAPI.addModule.mockImplementation(_ => Promise.resolve({
      index: 2,
      wfModule: { id: 40, foo: 'bar' }
    }))

    const store = mockStore(testState)
    await store.dispatch(wfr.addModuleAction('module2', 2, { x: 'y' }))

    expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(999, 2, 2, { x: 'y' })
  })

  it('adds a module before another', async () => {
    WorkbenchAPI.addModule.mockImplementation(_ => Promise.resolve({
      index: 2,
      wfModule: { id: 40, foo: 'bar' }
    }))

    const store = mockStore(testState)
    await store.dispatch(wfr.addModuleAction(1, { beforeWfModuleId: 20 }, { x: 'y' }))
    expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(999, 1, 1, { x: 'y' })
  })

  it('adds a module after another', async () => {
    WorkbenchAPI.addModule.mockImplementation(_ => Promise.resolve({
      index: 2,
      wfModule: { id: 40, foo: 'bar' }
    }))

    const store = mockStore(testState)
    await store.dispatch(wfr.addModuleAction(1, { afterWfModuleId: 20 }, { x: 'y' }))
    expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(999, 1, 2, { x: 'y' })
  })

  it('Deletes a module', async () => {
    WorkbenchAPI.deleteModule.mockImplementation(_ => Promise.resolve(null))
    const store = mockStore(testState)
    await store.dispatch(wfr.deleteModuleAction(20))

    expect(WorkbenchAPI.deleteModule).toHaveBeenCalledWith(20)
    const state = store.getState()
    expect(state.workflow.wf_modules).toEqual([ 10, 30 ])
    expect(state.wfModules['20']).not.toBeDefined()
  })

  it('sets the selected module to a module in state', async () => {
    WorkbenchAPI.setSelectedWfModule.mockImplementation(_ => Promise.resolve(null))
    const store = mockStore(testState)
    await store.dispatch(wfr.setSelectedWfModuleAction(1))

    expect(WorkbenchAPI.setSelectedWfModule).toHaveBeenCalledWith(999, 1)
    expect(store.getState().selected_wf_module).toEqual(1)
  })

  it('updates the workflow module with the specified data', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'UPDATE_WF_MODULE_PENDING',
      payload: {
        id: 20,
        data: {
          notifications: true
        }
      }
    })
    expect(state.wfModules['20'].notifications).toBe(true)
  })

  it('overwrites a workflow and its wfModules', () => {
    const state = wfr.workflowReducer(testState, wfr.setWorkflowAction({
      workflow: {
        id: 999,
        wf_modules: [ 1 ]
      },
      wfModules: {
        1: { id: 1 }
      }
    }))

    expect(state.workflow).toEqual({ id: 999, wf_modules: [ 1 ] })
    expect(state.wfModules).toEqual({ 1: { id: 1 } })
  })

  it('overwrites some wfModule properties', () => {
    const state = wfr.workflowReducer(testState, wfr.setWfModuleAction({
      id: 10,
      has_unseen_notification: false
    }))
    // Does not overwrite other wfModules
    expect(state.wfModules['20']).toBe(testState.wfModules['20'])
    // Does not overwrite unspecified properties
    expect(state.wfModules['10'].versions).toBe(state.wfModules['10'].versions)
    // Overwrites specified properties
    expect(state.wfModules['10'].has_unseen_notification).toBe(false)
  })

  it('does nothing if we update a nonexistent wfmodule', async () => {
    const store = mockStore(testState)
    await store.dispatch(wfr.updateWfModuleAction(40, { notifications: false }))

    expect(WorkbenchAPI.updateWfModule).not.toHaveBeenCalled()
    expect(store.getState()).toEqual(testState)
  })

  it('reorders modules', async () => {
    const store = mockStore(testState)
    WorkbenchAPI.reorderWfModules.mockImplementation(() => Promise.resolve(null))
    await store.dispatch(wfr.moveModuleAction(2, 0))

    // Change happens synchronously. No need to even await the promise :)
    expect(WorkbenchAPI.reorderWfModules).toHaveBeenCalledWith(999, [
      { id: 30, order: 0 },
      { id: 10, order: 1 },
      { id: 20, order: 2 }
    ])
    expect(store.getState().workflow.wf_modules).toEqual([ 30, 10, 20 ])
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
    expect(state.wfModules['10'].parameter_vals).toBe(testState.wfModules['10'].parameter_vals) // old property
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

  it('sets the wfModule status', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'SET_WF_MODULE_STATUS',
      payload: {
        wfModuleId: 20,
        status: 'error',
        error_msg: 'There was an error'
      }
    })

    expect(state.wfModules['20'].status).toEqual('error')
    expect(state.wfModules['20'].error_msg).toEqual('There was an error')

    const state2 = wfr.workflowReducer(state, {
      type: 'SET_WF_MODULE_STATUS',
      payload: {
        wfModuleId: 20,
        status: 'error',
        error_msg: 'There was another error'
      }
    })

    expect(state2.wfModules['20'].status).toEqual('error')
    expect(state2.wfModules['20'].error_msg).toEqual('There was another error')
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

  it('should setParamValueAction', async () => {
    WorkbenchAPI.onParamChanged.mockImplementation(_ => Promise.resolve({}))

    const store = mockStore(testState)
    const done = store.dispatch(wfr.setParamValueAction(1, { value: 'foo' }))

    // should set value immediately
    expect(store.getState().wfModules['10'].parameter_vals[0].value).toEqual('foo')
    await done

    // should send HTTP request
    expect(WorkbenchAPI.onParamChanged).toHaveBeenCalledWith(1, { value: 'foo' })
  })

  it('requests fetch in maybeRequestWfModuleFetchAction', async () => {
    WorkbenchAPI.requestFetch.mockImplementation(_ => Promise.resolve(null))
    const store = mockStore(testState)
    const done = store.dispatch(wfr.maybeRequestWfModuleFetchAction(10))

    // should set nClientRequests immediately.
    expect(store.getState().wfModules['10'].nClientRequests).toEqual(1)

    await done
    expect(store.getState().wfModules['10'].nClientRequests).toEqual(0)
  })

  it('should no-op when setting param value to itself', async () => {
    const store = mockStore(testState)
    await store.dispatch(wfr.setParamValueAction(1, { value: 'Some Data' }))

    // should send HTTP request
    expect(WorkbenchAPI.onParamChanged).not.toHaveBeenCalled()
  })

  it('should setParamValueActionByIdName', async () => {
    WorkbenchAPI.onParamChanged.mockImplementation(_ => Promise.resolve({}))

    const store = mockStore(testState)
    const done = store.dispatch(wfr.setParamValueActionByIdName(10, 'data', { value: 'foo' }))

    // should set value immediately
    expect(store.getState().wfModules['10'].parameter_vals[0].value).toEqual('foo')

    // should send HTTP request
    expect(WorkbenchAPI.onParamChanged).toHaveBeenCalledWith(1, { value: 'foo' })
    await done
  })

  it('Sets the data version', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'SET_DATA_VERSION_PENDING',
      payload: {
        wfModuleId: 10,
        selectedVersion: "2018-02-21T03:09:10.214054Z"
      }
    });
    expect(state.wfModules['10'].versions.selected).toBe("2018-02-21T03:09:10.214054Z");
  });

  it('Marks the data versions read', async () => {
    WorkbenchAPI.markDataVersionsRead.mockImplementation(_ => Promise.resolve({}))

    const store = mockStore(testState)
    const done = store.dispatch(wfr.markDataVersionsReadAction(10, ["2018-02-21T03:09:15.214054Z", "2018-02-21T03:09:10.214054Z"]))

    // state changed before send
    const state = store.getState()
    expect(state.wfModules['10'].versions.versions[1][1]).toBe(true)
    expect(state.wfModules['10'].versions.versions[2][1]).toBe(true)

    await done

    // API request sent and received
    expect(WorkbenchAPI.markDataVersionsRead).toHaveBeenCalledWith(10, ["2018-02-21T03:09:15.214054Z", "2018-02-21T03:09:10.214054Z"])
  })

  it('Clears the notification count', () => {
    const state = wfr.workflowReducer(testState, {
      type: 'CLEAR_NOTIFICATIONS_PENDING',
      payload: {
        wfModuleId: 10
      }
    });
    expect(state.wfModules['10'].has_unseen_notification).toBe(false);
  });
});
