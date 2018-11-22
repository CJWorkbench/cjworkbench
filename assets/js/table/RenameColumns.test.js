import { updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'

jest.mock('../workflow-reducer')
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'


describe('RenameColumns actions', () => {
  // A few parameter id constants for readability
  const initialState = {
    workflow: {
      wf_modules: [ 35, 50, 85 ],
    },
    modules: {
      24: { id_name: 'rename-columns' },
      1: { id_name: 'loadurl' },
      2: { id_name: 'filter' }
    },
    wfModules: {
      35: { id: 35, module_version: { module: 1 } },
      50: { id: 50, module_version: { module: 2 } },
      85: {
        id: 85,
        module_version: { module: 24 },
        parameter_vals: [
          {
            parameter_spec: {
              id_name: 'rename-entries'
            },
            value: JSON.stringify({
              'name': 'host_name',
              'narrative': 'nrtv'
            })
          }
        ]
      }
    }
  }

  const addModuleResponse = {
    data: {
      wfModule: {
        id: 99,
        module_version: { module: 24 },
        parameter_vals: [
          {
            parameter_spec: {
              id_name: 'rename-entries'
            },
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

  it('adds a new rename module after the current non-rename module', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(35, 'rename-columns', false, { prevName: 'cornerstone', newName: 'cs' })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('rename-columns', 1)
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 99, { 'rename-entries': JSON.stringify({ cornerstone: 'cs' }) }])
  })

  it('adds a new column to an existing rename module', async () => {
    updateTableActionModule(50, 'rename-columns', false, { prevName: 'cornerstone', newName: 'cs' })

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 85, { 'rename-entries': JSON.stringify({ name: 'host_name', narrative: 'nrtv', cornerstone: 'cs' }) }])
  })

  it('renames an already-renamed column', async () => {
    updateTableActionModule(50, 'rename-columns', false, { prevName: 'host_name', newName: 'host' })

    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 85, { 'rename-entries': JSON.stringify({ name: 'host', narrative: 'nrtv' }) }])
  })
})
