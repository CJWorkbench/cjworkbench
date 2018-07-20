import {updateTableActionModule} from './UpdateTableAction'

jest.mock('./workflow-reducer')
import { store, addModuleAction, setParamValueAction, setSelectedWfModuleAction } from './workflow-reducer'

describe('Edit Cell actions', () => {
  const idName = 'editcells'
  const Edit1 = { row: 3, col: 'foo', value: 'bar' }
  const Edit2 = { row: 10, col: 'bar', value: 'yippee!' }

  // Stripped down workflow object, only what we need for testing cell editing
  const test_workflow = {
    id: 999,
    wf_modules: [
      {
        id: 10,
        module_version : {
          module: {
            id_name: 'loadurl'
          }
        }
      },
      {
        // Existing Edit Cells module with existing edits
        id: 20,
        module_version : {
          module : {
            id_name: idName
          }
        },
        parameter_vals: [
          {
            id: 101,
            parameter_spec: { id_name: 'celledits' },
            value: JSON.stringify([ Edit1 ]),
          }
        ]
      },
      {
        id: 30,
        module_version : {
          module: {
            id_name: 'filter'
          }
        }
      },
      {
        id: 40,
        module_version : {
          module: {
            id_name: 'dropna'
          }
        }
      },
    ],
  }

  // mocked data from api.addModule call, looks like a just-added edit cells module
  const addModuleResponse = {
    id: 99,
    module_version : {
      module : {
        id_name: idName
      }
    },
    parameter_vals: [
      {
        id: 999,
        parameter_spec: { id_name: 'celledits' },
        value: ''
      }
    ]
  }

  const initialState = {
    workflow: test_workflow,
    updateTableModuleIds: {'editcells': 5000}
  }

  beforeEach(() => {
    store.getState.mockImplementation(() => initialState)
    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      }
    })

    setParamValueAction.mockImplementation((...args) => [ 'setParamValueAction', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds edit to existing Edit Cell module', () => {
    updateTableActionModule(20, idName, Edit2)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', 101, JSON.stringify([ Edit1, Edit2 ]) ])
  })

  it('selects the Edit Cell module it is editing', () => {
    updateTableActionModule(20, idName, Edit2)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 1 ])
  })

  it('adds edit to immediately-following Edit Cell module', () => {
    updateTableActionModule(10, idName, Edit2)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', 101, JSON.stringify([ Edit1, Edit2 ]) ])
  })

  it('adds new Edit Cells module before end of stack', (done) => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(30, idName, Edit2)

    expect(addModuleAction).toHaveBeenCalledWith(initialState.updateTableModuleIds[idName], 3)

    // let addModule promise resolve
    setImmediate(() => {
      expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', 999, JSON.stringify([ Edit2 ]) ])
      done()
    })
  })

  it('add new Edit Cells module to end of stack', () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(40, idName, {row: 10, col:'bar', 'value':'yippee!'})
    expect(addModuleAction).toHaveBeenCalledWith(initialState.updateTableModuleIds[idName], 4)
  })
})
