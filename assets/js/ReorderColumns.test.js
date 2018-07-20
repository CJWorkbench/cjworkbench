import { updateTableActionModule } from './UpdateTableAction'
import { tick } from './test-utils'
import { store, addModuleAction, setParamValueAction, setParamValueActionByIdName, setSelectedWfModuleAction } from './workflow-reducer'

jest.mock('./workflow-reducer')

describe('ReorderColumns actions', () => {

  // A few parameter id constants for better readability
  const idName = 'reorder-columns'
  const LOADURL_WFM_ID = 35

  const FILTER_WFM_ID = 50

  const REORDER_WFM_ID = 85
  const REORDER_HISTORY_PAR_ID = 90

  const NEW_REORDER_WFM_ID = 135
  const NEW_REORDER_HISTORY_PAR_ID = 105

  const REORDER_MODULE_ID = 24
  const WF_ID = 10

  var initialState = {
    reorderModuleId: REORDER_MODULE_ID,
    workflow: {
      id: WF_ID,
      wf_modules: [
        {
          id: LOADURL_WFM_ID,
          module_version: {
            module: {
              id_name: 'loadurl'
            }
          }
        },
        {
          id: FILTER_WFM_ID,
          module_version: {
            module: {
              id_name: 'filter'
            }
          }
        },
        {
          id: REORDER_WFM_ID,
          module_version: {
            module: {
              id_name: idName
            },
          },
          parameter_vals: [
            {
              id: REORDER_HISTORY_PAR_ID,
              parameter_spec: {
                id_name: 'reorder-history'
              },
              value: JSON.stringify([{
                column: 'existing_test_col',
                from: 2,
                to: 4
              }])
            }
          ]
        }
      ]
    }
  }

  const addModuleResponse = {
    id: NEW_REORDER_WFM_ID,
    module_version: {
      module: {
        id_name: idName
      }
    },
    parameter_vals: [
      {
        id: NEW_REORDER_HISTORY_PAR_ID,
        parameter_spec: {
          id_name: 'reorder-history'
        },
        value: ''
      }
    ]
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
    setParamValueActionByIdName.mockImplementation((...args) => [ 'setParamValueActionByIdName', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
    addModuleAction.mockImplementation(() => () => addModuleResponse)
  });


  it('Adds a new reorder module', async () => {
    updateTableActionModule(LOADURL_WFM_ID, idName, { column: 'test_col', from: 3, to: 0 })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith(initialState.reorderModuleId, 1)
    let newParamVal = JSON.stringify([{
      column: 'test_col',
      from: 3,
      to: 0
    }])
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', NEW_REORDER_HISTORY_PAR_ID, newParamVal ])
  })


  it('Updates the parameter values of an adjacent reorder module correctly', async () => {
    updateTableActionModule(FILTER_WFM_ID, idName, { column: 'test_col', from: 3, to: 0 })

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
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', REORDER_HISTORY_PAR_ID, newParamVal ])
  })

  it('Updates the parameter values of the currently selected reorder module correctly', async () => {
    updateTableActionModule(REORDER_WFM_ID, idName, { column: 'test_col', from: 3, to: 0 })

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
    expect(store.dispatch).toHaveBeenCalledWith([ 'setParamValueAction', REORDER_HISTORY_PAR_ID, newParamVal ])
  })

})
