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
          wfModuleId={99}
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
      WorkbenchAPI.setWfModuleParams.mockReset()
      WorkbenchAPI.setSelectedWfModule.mockReset()
    })

    const wrapper = (modules=null, wf_module_ids=null, wfModules=null, extraProps={}) => {
      if (wf_module_ids === null) {
        wf_module_ids = [99, 100, 101]
      }

      if (wfModules === null) {
        wfModules = {
          '99': {
            tab_id: 11,
            module_version: { module: 10 },
            parameter_vals: [ { parameter_spec: { id_name: 'foo10' }, value: 'bar10' } ]
          },
          '100': {
            tab_id: 11,
            module_version: { module: 20 },
            parameter_vals: [ { parameter_spec: { id_name: 'foo20' }, value: 'bar20' } ]
          }
        }
      }

      if (modules === null) {
        modules = {
          '10': { row_action_menu_entry_title: 'Foo these rows' },
          '20': { row_action_menu_entry_title: 'Bar these rows' }
        }
      }

      const store = mockStore({
        modules,
        wfModules,
        tabs: { 11: { id: 11, wf_module_ids } },
        workflow: { id: 321, tab_ids: [ 11, 12 ], selected_tab_position: 0 }
      })
      return mount(
        <Provider store={store}>
          <ConnectedSelectedRowsActions
            selectedRowIndexes={[3, 1, 4]}
            wfModuleId={99}
            onClickRowsAction={jest.fn()}
            {...extraProps}
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
      const w = wrapper({
        '15': {}, // the dream: JSON does not contain title
        '16': { row_action_menu_entry_title: '' } // reality: JSON contains empty-string title
      })
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.find('button')).toHaveLength(1)
    })

    it('should use addModuleAction', async () => {
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
      expect(WorkbenchAPI.addModule).toHaveBeenCalledWith(321, 15, 1, { rows: '2, 4-5' })
    })

    it('should use setWfModuleParams action, fromInput', async () => {
      WorkbenchAPI.setWfModuleParams.mockImplementation(_ => Promise.resolve(null))
      WorkbenchAPI.setSelectedWfModule.mockImplementation(_ => Promise.resolve(null))

      const w = wrapper(
        {
          '10': {},
          '20': {
            id: 20,
            row_action_menu_entry_title: 'Baz these rows',
            js_module: 'module.exports = { addSelectedRows: (oldParams, rows, fromInput) => ({ oldParams, rows, fromInput }) }'
          }
        },
        [ 99, 100 ],
        null, // wrapper() defaults to wfModule 99 has module 10, wfModule 100 has module 20
        { wfModuleId: 99 } // we'll edit 100 from wfModule 99
      )
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.text()).toMatch(/Baz these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(WorkbenchAPI.setSelectedWfModule).toHaveBeenCalledWith(321, 1)
      expect(WorkbenchAPI.setWfModuleParams).toHaveBeenCalledWith(
        100,
        { oldParams: { foo20: 'bar20' }, rows: '2, 4-5', fromInput: true }
      )
    })

    it('should use setWfModuleParams action, fromInput=false (from output)', async () => {
      WorkbenchAPI.setWfModuleParams.mockImplementation(_ => Promise.resolve(null))

      const w = wrapper(
        {
          '10': {
            id: 10,
            row_action_menu_entry_title: 'Baz these rows',
            js_module: 'module.exports = { addSelectedRows: (oldParams, rows, fromInput) => ({ oldParams, rows, fromInput }) }'
          },
          '20': {
          }
        },
        [ 99, 100 ],
        null, // wrapper() defaults to wfModule 99 has module 10, wfModule 100 has module 20
        { wfModuleId: 99 } // we'll edit 99 from wfModule 99
      )
      w.find('button').at(0).simulate('click')
      w.update()
      expect(w.text()).toMatch(/Baz these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(WorkbenchAPI.setWfModuleParams).toHaveBeenCalledWith(
        99,
        { oldParams: { foo10: 'bar10' }, rows: '2, 4-5', fromInput: false }
      )
    })
  })
})
