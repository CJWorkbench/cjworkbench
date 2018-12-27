import { updateTableAction } from './UpdateTableAction'
import { addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe("UpdateTableAction actions", () => {
  beforeEach(() => {
    addModuleAction.mockImplementation((...args) => [ 'addModuleAction', ...args ])
    setWfModuleParamsAction.mockImplementation((...args) => [ 'setWfModuleParamsAction', ...args ])
    setSelectedWfModuleAction.mockImplementation((...args) => [ 'setSelectedWfModuleAction', ...args ])
  })

  let _alert
  beforeEach(() => {
    _alert = window.alert
    window.alert = jest.fn()
  })
  afterEach(() => {
    window.alert = _alert
  })

  it('should alert user if module is not imported', async () => {
    const dispatch = jest.fn()
    const getState = () => ({
      wfModules: {
        17: { module: 'loadurl' },
      },
      modules: {
        loadurl: {}
        // 'filter' is not present -- so we'll get an error
      }
    })

    updateTableAction(17, 'filter', true, { columnKey: 'A' })(dispatch, getState)
    expect(window.alert).toHaveBeenCalledWith("Module 'filter' not imported.")
    expect(dispatch).not.toHaveBeenCalled()
  })

  it('should select and update an existing module after the selected one', () => {
    const getState = () => ({
      tabs: {
        2: { wf_module_ids: [ 10, 11 ], selected_wf_module_position: 0 }
      },
      wfModules: {
        10: { tab_id: 2 },
        11: { tab_id: 2, module: 'filter', params: { column: 'A' }}
      },
      modules: {
        loadurl: {},
        filter: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(10, 'filter', false, { columnKey: 'B' })(dispatch, getState)
    expect(dispatch).toHaveBeenCalledWith([ 'setSelectedWfModuleAction', 11 ])
    expect(dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 11, { column: 'B' } ])
  })

  it('should update an existing, selected module', () => {
    const getState = () => ({
      tabs: {
        2: { wf_module_ids: [ 10, 11 ], selected_wf_module_position: 1 }
      },
      wfModules: {
        10: {},
        11: { tab_id: 2, module: 'filter', params: { column: 'A' }}
      },
      modules: {
        loadurl: {},
        filter: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'filter', false, { columnKey: 'B' })(dispatch, getState)
    expect(dispatch).toHaveBeenCalledWith([ 'setWfModuleParamsAction', 11, { column: 'B' } ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should insert a new module when the current+next have the wrong id_name', () => {
    const getState = () => ({
      tabs: {
        2: { wf_module_ids: [ 10, 11, 12, 13 ] }
      },
      wfModules: {
        10: { module: 'filter' },
        11: { tab_id: 2, module: 'sort' },
        12: { module: 'sort' },
        13: { module: 'filter' }
      },
      modules: {
        filter: {},
        sort: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'filter', false, { columnKey: 'B' })(dispatch, getState)
    expect(dispatch).toHaveBeenCalledWith([ 'addModuleAction', 'filter', { afterWfModuleId: 11 }, { column: 'B' } ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should insert a new module when forceNewModule', () => {
    const getState = () => ({
      tabs: {
        2: { wf_module_ids: [ 10, 11 ] }
      },
      wfModules: {
        10: { tab_id: 2, module: 'filter' },
        11: { module: 'filter' }
      },
      modules: {
        filter: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(10, 'filter', true, { columnKey: 'B' })(dispatch, getState)
    expect(dispatch).toHaveBeenCalledWith([ 'addModuleAction', 'filter', { afterWfModuleId: 10 }, { column: 'B' } ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should append a new module to the end of the tab', () => {
    const getState = () => ({
      tabs: {
        2: { wf_module_ids: [ 10, 11 ] }
      },
      wfModules: {
        10: { module: 'fetch' },
        11: { tab_id: 2, module: 'sort' }
      },
      modules: {
        filter: {},
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'filter', false, { columnKey: 'B' })(dispatch, getState)
    expect(dispatch).toHaveBeenCalledWith([ 'addModuleAction', 'filter', { afterWfModuleId: 11 }, { column: 'B' } ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })
})
