jest.mock('../WorkbenchAPI')

import React from 'react'
import { mount } from 'enzyme'
import { mockStore } from '../workflow-reducer'
import { Provider } from 'react-redux'
import { tick } from '../test-utils'
import WorkbenchAPI from '../WorkbenchAPI'
import ConnectedSelectedRowsActions, { SelectedRowsActions } from './SelectedRowsActions'

describe('SelectedRowsActions', () => {
  describe('standalone', () => {
    const wrapper = (extraProps={}) => {
      return mount(
        <SelectedRowsActions
          selectedRowIndexes={[3, 1, 4]}
          selectedWfModuleId={99}
          rowActionModules={[
            { id: 10, title: 'Foo these rows' },
            { id: 20, title: 'Bar these rows' }
          ]}
          onClickRowsAction={jest.fn()}
          {...extraProps}
        />
      )
    }

    it('should render number of selected columns', () => {
      const w = wrapper({ selectedRowIndexes: [ 2, 5, 6 ] })
      expect(w.text()).toMatch(/3 rows selected/)
    })

    it('should not appear when there are no rows', () => {
      const w = wrapper({ selectedRowIndexes: [] })
      expect(w.text()).toBe(null)
    })

    it('should not appear when there is no selectedWfModuleId', () => {
      const w = wrapper({ selectedWfModuleId: null })
      expect(w.text()).toBe(null)
    })

    it('should invoke an action with rows as a string, 1-based', () => {
      const w = wrapper({ selectedRowIndexes: [ 2, 3, 4, 5, 8000, 8001, 8002, 9 ] })
      w.find('button').at(0).simulate('click') // open the menu
      w.update()
      w.find('button').at(1).simulate('click')
      expect(w.prop('onClickRowsAction')).toHaveBeenCalledWith(99, 10, '3-6, 10, 8001-8003')
    })
  })

  describe('connected', () => {
    beforeEach(() => {
      WorkbenchAPI.addModule.mockReset()
      WorkbenchAPI.onParamChanged.mockReset()
    })

    const wrapper = (modules=null, wf_modules=null) => {
      if (wf_modules === null) {
        wf_modules = [99, 100, 101]
      }

      if (modules === null) {
        modules = {
          '10': { row_action_menu_entry_title: 'Foo these rows' },
          '20': { row_action_menu_entry_title: 'Bar these rows' }
        }
      }

      const store = mockStore({ modules, workflow: { id: 321, wf_modules } })
      return mount(
        <Provider store={store}>
          <ConnectedSelectedRowsActions
            selectedRowIndexes={[3, 1, 4]}
            selectedWfModuleId={99}
            onClickRowsAction={jest.fn()}
          />
        </Provider>
      )
    }

    it('should render modules', () => {
      const w = wrapper({ '15': { row_action_menu_entry_title: 'Baz these rows' } })
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.text()).toMatch(/Baz these rows/)
    })

    it('should not render modules that do not belong', () => {
      const w = wrapper({ '15': { name: 'Baz columns' } })
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.text()).not.toMatch(/Baz/)
    })

    it('should dispatch the correct actions', async () => {
      WorkbenchAPI.addModule.mockImplementation(_ => Promise.resolve({
        index: 1,
        wfModule: {
          id: 103,
          module_version: { module: 15 },
          parameter_vals: [
            { id: 123, value: '', parameter_spec: { id_name: 'rows', type: 'string' } }
          ]
        }
      }))

      WorkbenchAPI.onParamChanged.mockImplementation(_ => Promise.resolve(null))

      const w = wrapper({
        '15': {
          row_action_menu_entry_title: 'Baz these rows',
        }
      })
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.text()).toMatch(/Baz these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(321, 15, 1)
      expect(WorkbenchAPI.onParamChanged).toHaveBeenCalledWith(123, { value: '2, 4-5' })
    })
  })
})
