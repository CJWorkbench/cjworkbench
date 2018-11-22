import { updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe('ReorderColumns actions', () => {
  const initialState = {
    workflow: { wf_modules: [ 35, 50, 85 ] },
    modules: {
      24: { id_name: 'reorder-columns' },
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
            parameter_spec: { id_name: 'reorder-history' },
            value: JSON.stringify([{
              column: 'existing_test_col',
              from: 2,
              to: 4
            }])
          }
        ]
      }
    }
  }

  const addModuleResponse = {
    data: {
      wfModule: {
        id: 99,
        module_version: {
          module: {
            id_name: 'reorder-columns',
          }
        },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'reorder-history' },
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

    addModuleAction.mockReset()
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    setWfModuleParamsAction.mockReset()
    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockReset()
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })


  it('Adds a new reorder module', async () => {
    updateTableActionModule(35, 'reorder-columns', false, { column: 'test_col', from: 3, to: 0 })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('reorder-columns', 1)
    let newParamVal = JSON.stringify([{
      column: 'test_col',
      from: 3,
      to: 0
    }])
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 99, { 'reorder-history': newParamVal }])
  })


  it('Updates the parameter values of an adjacent reorder module correctly', async () => {
    updateTableActionModule(50, 'reorder-columns', false, { column: 'test_col', from: 3, to: 0 })

    await tick()

    let newParamVal = JSON.stringify([
      {
        column: 'existing_test_col',
        from: 2,
        to: 4
      },
      {
        column: 'test_col',
        from: 3,
        to: 0
      }])
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 85, { 'reorder-history': newParamVal }])
  })

  it('Updates the parameter values of the currently selected reorder module correctly', async () => {
    updateTableActionModule(85, 'reorder-columns', false, { column: 'test_col', from: 3, to: 0 })

    await tick()

    let newParamVal = JSON.stringify([
      {
        column: 'existing_test_col',
        from: 2,
        to: 4
      },
      {
        column: 'test_col',
        from: 3,
        to: 0
      }])
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 85, { 'reorder-history': newParamVal }])
  })

})
