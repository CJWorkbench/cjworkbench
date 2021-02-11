/* globals it, jest, expect, describe, beforeEach, afterEach */
import { updateTableAction } from './UpdateTableAction'
import {
  addStepAction,
  setStepParamsAction,
  setSelectedStepAction
} from '../workflow-reducer'

jest.mock('../workflow-reducer')

describe('UpdateTableAction actions', () => {
  beforeEach(() => {
    addStepAction.mockImplementation((...args) => ['addStepAction', ...args])
    setStepParamsAction.mockImplementation((...args) => [
      'setStepParamsAction',
      ...args
    ])
    setSelectedStepAction.mockImplementation((...args) => [
      'setSelectedStepAction',
      ...args
    ])
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
      steps: {
        17: { module: 'loadurl' }
      },
      modules: {
        loadurl: {}
        // 'filter' is not present -- so we'll get an error
      }
    })

    updateTableAction(17, 'filter', true, { columnKey: 'A' })(
      dispatch,
      getState
    )
    expect(window.alert).toHaveBeenCalledWith("Module 'filter' not imported.")
    expect(dispatch).not.toHaveBeenCalled()
  })

  it('should select and update an existing module after the selected one', () => {
    const getState = () => ({
      tabs: {
        'tab-2': { step_ids: [10, 11], selected_step_position: 0 }
      },
      steps: {
        10: { tab_slug: 'tab-2' },
        11: {
          tab_slug: 'tab-2',
          module: 'duplicatecolumns',
          params: { colnames: ['A'] }
        }
      },
      modules: {
        loadurl: {},
        duplicatecolumns: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(10, 'duplicatecolumns', false, { columnKey: 'B' })(
      dispatch,
      getState
    )
    expect(dispatch).toHaveBeenCalledWith(['setSelectedStepAction', 11])
    expect(dispatch).toHaveBeenCalledWith([
      'setStepParamsAction',
      11,
      { colnames: ['A', 'B'] }
    ])
  })

  it('should insert a new module when the current+next have the wrong id_name', () => {
    const getState = () => ({
      tabs: {
        'tab-2': { step_ids: [10, 11, 12, 13] }
      },
      steps: {
        10: { module: 'clean-text' },
        11: { tab_slug: 'tab-2', module: 'sort' },
        12: { module: 'sort' },
        13: { module: 'clean-text' }
      },
      modules: {
        'clean-text': {},
        sort: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'clean-text', false, { columnKey: 'B' })(
      dispatch,
      getState
    )
    expect(dispatch).toHaveBeenCalledWith([
      'addStepAction',
      'clean-text',
      { afterStepId: 11 },
      { colnames: ['B'] }
    ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should update an existing, selected module', () => {
    const getState = () => ({
      tabs: {
        'tab-2': { step_ids: [10, 11], selected_step_position: 1 }
      },
      steps: {
        10: {},
        11: {
          tab_slug: 'tab-2',
          module: 'duplicatecolumns',
          params: { colnames: ['A'] }
        }
      },
      modules: {
        loadurl: {},
        duplicatecolumns: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'duplicatecolumns', false, { columnKey: 'B' })(
      dispatch,
      getState
    )
    expect(dispatch).toHaveBeenCalledWith([
      'setStepParamsAction',
      11,
      { colnames: ['A', 'B'] }
    ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should insert a new module when forceNewModule', () => {
    const getState = () => ({
      tabs: {
        'tab-2': { step_ids: [10, 11] }
      },
      steps: {
        10: { tab_slug: 'tab-2', module: 'filter' },
        11: { module: 'filter' }
      },
      modules: {
        filter: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(10, 'filter', true, { columnKey: 'B' })(
      dispatch,
      getState
    )
    expect(dispatch).toHaveBeenCalledWith([
      'addStepAction',
      'filter',
      { afterStepId: 10 },
      {
        keep: true,
        condition: {
          operation: 'and',
          conditions: [
            {
              operation: 'and',
              conditions: [
                {
                  operation: '',
                  column: 'B',
                  value: '',
                  isCaseSensitive: false,
                  isRegex: false
                }
              ]
            }
          ]
        }
      }
    ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })

  it('should append a new module to the end of the tab', () => {
    const getState = () => ({
      tabs: {
        'tab-2': { step_ids: [10, 11] }
      },
      steps: {
        10: { module: 'fetch' },
        11: { tab_slug: 'tab-2', module: 'sort' }
      },
      modules: {
        filter: {}
      }
    })
    const dispatch = jest.fn()
    updateTableAction(11, 'filter', false, { columnKey: 'B' })(
      dispatch,
      getState
    )
    expect(dispatch).toHaveBeenCalledWith([
      'addStepAction',
      'filter',
      { afterStepId: 11 },
      {
        keep: true,
        condition: {
          operation: 'and',
          conditions: [
            {
              operation: 'and',
              conditions: [
                {
                  operation: '',
                  column: 'B',
                  value: '',
                  isCaseSensitive: false,
                  isRegex: false
                }
              ]
            }
          ]
        }
      }
    ])
    expect(dispatch).toHaveBeenCalledTimes(1) // no 'select' call
  })
})
