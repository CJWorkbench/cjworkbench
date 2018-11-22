import { extractNumberAny, updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("ExtractNumbers actions", () => {
  const initialState = {
    workflow: {
      id: 127,
      wf_modules: [ 17, 7, 19, 31, 79 ]
    },
    modules: {
      1: { id_name: 'loadurl' },
      2: { id_name: 'filter' },
      77: { id_name: 'extract-numbers' }
    },
    wfModules: {
      17: { id: 17, module_version: { module: 1 } },
      7: {
        // An existing extract module
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'num_col'
          },
          {
            parameter_spec: {id_name: 'extract'},
            value: false
          },
          {
            parameter_spec: {id_name: 'type_format'},
            value: 0
          },
          {
            parameter_spec: {id_name: 'type_replace'},
            value: 0
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 2 } },
      79: {
        // Another existing extract module, set to Int type
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: 'num_col'
          },
          {
            parameter_spec: {id_name: 'extract'},
            value: true
          },
          {
            parameter_spec: {id_name: 'type_format'},
            value: 0
          },
          {
            parameter_spec: {id_name: 'type_replace'},
            value: 1
          }
        ]
      }
    }
  }
  const addModuleResponse = {
    data: {
      index: 2,
      wfModule: {
        id: 99,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: {id_name: 'colnames'},
            value: ''
          }
        ]
      }
    }
  }


  beforeEach(() => {
    store.getState.mockReset()
    store.getState.mockImplementation(() => initialState)
    // Our shim Redux API:
    // 1) actions are functions; dispatch returns their retvals in a Promise.
    //    This is useful when we care about retvals.
    // 2) actions are _not_ functions; dispatch does nothing. This is useful when
    //    we care about arguments.
    store.dispatch.mockReset()
    store.dispatch.mockImplementation(action => {
      if (typeof action === 'function') {
        return Promise.resolve({ value: action() })
      }
    })

    setWfModuleParamsAction.mockReset()
    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockReset()
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds new extract module after the given module and sets type to "Any"', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(19, 'extract-numbers', false, {columnKey: 'num_col'})

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('extract-numbers', 3)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 99, { colnames: 'num_col', type: extractNumberAny }])
  })

  it('selects the existing extract module with defaults and adds column', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'extract-numbers', false, {columnKey: 'str_col'})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { colnames: 'num_col,str_col' }])
  })

  it('selects the existing extract module with same column and does nothing', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'extract-numbers', false, {columnKey: 'num_col'})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith(["setSelectedWfModuleAction", 1])
  })

  it('should force a new module when an existing one has no defaults', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(79, 'extract-numbers', false, {columnKey: 'str_col'})

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('extract-numbers', 5)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 99, { colnames: 'str_col', type: extractNumberAny }])
  })
})
