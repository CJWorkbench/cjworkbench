import { sortDirectionAsc, sortDirectionDesc, sortDirectionNone, updateTableActionModule } from './UpdateTableAction'
import { tick } from '../test-utils'
import { store, addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("SortFromTable actions", () => {
  // A few parameter id constants for better readability
  const initialState = {
    workflow: {
      id: 127,
      tab_ids: [ 10, 11 ],
      selected_tab_position: 1
    },
    tabs: {
      11: { wf_module_ids: [ 17, 7, 19, 31, 79 ] }
    },
    modules: {
      1: { id_name: 'loadurl' },
      2: { id_name: 'filter' },
      77: { id_name: 'sort-from-table' }
    },
    wfModules: {
      17: { id: 17, module_version: { module: 1 } },
      7: {
        // An existing sort module
        id: 7,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'column' },
            value: ''
          },
          {
            parameter_spec: { id_name: 'dtype' },
            value: 0   // String
          },
          {
            parameter_spec: { id_name: 'direction' },
            value: 0     // Select
          }
        ]
      },
      19: { module_version: { module: 2 } },
      31: { module_version: { module: 2 } },
      79: {
        // Another existing sort module, set to num_col descending
        id: 79,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'column' },
            value: 'num_col'
          },
          {
            parameter_spec: { id_name: 'dtype' },
            value: 1   // Number
          },
          {
            parameter_spec: { id_name: 'direction' },
            value: 2   // Descending
          }
        ]
      }
    }
  }

  const addModuleResponse = {
    data: {
      wfModule: {
        id: 23,
        module_version: { module: 77 },
        parameter_vals: [
          {
            parameter_spec: { id_name: 'column' },
            value: ''
          },
          {
            parameter_spec: { id_name: 'dtype' },
            value: 0,
          },
          {
            parameter_spec: { id_name: 'direction' },
            value: 0
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

    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  it('adds new sort module after the given module and sets sort parameters', async () => {
    addModuleAction.mockImplementation(() => () => addModuleResponse)
    updateTableActionModule(19, 'sort-from-table', false, { columnKey: 'num_col', sortType: 'number', sortDirection: sortDirectionAsc })

    await tick()
    expect(addModuleAction).toHaveBeenCalledWith('sort-from-table', { tabId: 11, index: 3 })
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 23, { column: 'num_col', dtype: 1, direction: sortDirectionAsc }])
  })

  it('selects the existing sort module when updating it', async () => {
    store.getState.mockImplementation(() => Object.assign({}, initialState, { selected_wf_module: 0 }))
    updateTableActionModule(17, 'sort-from-table', false, { columnKey: 'str_col', columnType: 'text' })

    expect(store.dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 1 ])
  })

  it('orders a String column ascending by default', async () => {
    // Click on 'str_col' once, which should give us ascending order
    updateTableActionModule(17, 'sort-from-table', false, {columnKey: 'str_col', sortType: 'text', sortDirection: sortDirectionAsc})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { column: 'str_col', dtype: 0, direction: sortDirectionAsc }])
  })

  it('orders a Number column descending by default', async () => {
    // TODO revisit requirement. adamhooper does not agree that different types should get different orders by default
    updateTableActionModule(17, 'sort-from-table', false, {columnKey: 'num_col', sortType: 'number', sortDirection: sortDirectionDesc})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { column: 'num_col', dtype: 1, direction: sortDirectionDesc }])
  })

  it('orders a Data column descending by default', async () => {
    // TODO revisit requirement. adamhooper does not agree that different types should get different orders by default
    updateTableActionModule(17, 'sort-from-table', false, {columnKey: 'date_col', sortType: 'datetime', sortDirection: sortDirectionDesc})

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 7, { column: 'date_col', dtype: 2, direction: sortDirectionDesc }])
  })

  it('resets ordering state when changing sort column', async () => {
    // sort 79 is for 'num_col' in initial state. Change to 'str_col' and expect ascending order
    updateTableActionModule(79, 'sort-from-table', false, { columnKey: 'str_col', sortType: 'text', sortDirection: sortDirectionAsc })

    await tick()
    expect(store.dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 79, { column: 'str_col', dtype: 0, direction: sortDirectionAsc }])
  })
})
