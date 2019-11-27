/* globals beforeEach, describe, expect, it, jest */
import React from 'react'
import { mountWithI18n } from '../i18n/test-utils'
import { Provider } from 'react-redux'
import { mockStore, tick } from '../test-utils'
import { generateSlug } from '../utils'
import ConnectedSelectedRowsActions, { SelectedRowsActions } from './SelectedRowsActions'

jest.mock('../utils')

describe('SelectedRowsActions', () => {
  describe('standalone', () => {
    const wrapper = (extraProps = {}) => {
      return mountWithI18n(
        <SelectedRowsActions
          selectedRowIndexes={[3, 1, 4]}
          wfModuleId={99}
          rowActionModules={[
            { idName: 'dofoo', title: 'Foo these rows' },
            { idName: 'dobar', title: 'Bar these rows' }
          ]}
          onClickRowsAction={jest.fn()}
          {...extraProps}
        />
      )
    }

    it('should render number of selected columns', () => {
      const w = wrapper({ selectedRowIndexes: [2, 5, 6] })
      expect(w.find('Trans[id="js.table.SelectedRowsActions.numberOfSelectedRows"]').prop('values')).toEqual({ 0: '3' })
    })

    it('should invoke an action with rows as a string, 1-based', () => {
      const w = wrapper({ selectedRowIndexes: [2, 3, 4, 5, 8000, 8001, 8002, 9] })
      w.find('button.table-action').simulate('click') // open the menu
      w.find('button').at(1).simulate('click')
      expect(w.prop('onClickRowsAction')).toHaveBeenCalledWith(99, 'dofoo', '3-6, 10, 8001-8003')
    })
  })

  describe('connected', () => {
    let api

    beforeEach(() => {
      api = {
        addModule: jest.fn(() => Promise.resolve(null)),
        setWfModuleParams: jest.fn(() => Promise.resolve(null)),
        setSelectedWfModule: jest.fn(() => Promise.resolve(null))
      }
    })

    const wrapper = (state, extraProps = {}) => {
      const store = mockStore(state, api)
      return mountWithI18n(
        <Provider store={store}>
          <ConnectedSelectedRowsActions
            selectedRowIndexes={[3, 1, 4]}
            wfModuleId={2}
            onClickRowsAction={jest.fn()}
            {...extraProps}
          />
        </Provider>
      )
    }

    it('should render modules', () => {
      const w = wrapper({
        modules: {
          dofoo: {
            row_action_menu_entry_title: 'Foo these rows'
          }
        }
      })
      w.find('button.table-action').simulate('click') // open the menu
      expect(w.find('.dropdown-menu').text()).toMatch(/Foo these rows/)
    })

    it('should not render modules that do not belong', () => {
      const w = wrapper({
        modules: {
          dofoo: {
            row_action_menu_entry_title: '' // reality: JSON contains empty-string title
          }
        }
      })
      w.find('button.table-action').simulate('click') // open the menu
      expect(w.find('button')).toHaveLength(1)
    })

    it('should use addModuleAction', async () => {
      generateSlug.mockImplementation(prefix => prefix + 'X')

      const w = wrapper({
        tabs: { 'tab-1': { wf_module_ids: [2] } },
        wfModules: {
          2: { module: 'dofoo', tab_slug: 'tab-1' }
        },
        modules: {
          dobar: {
            row_action_menu_entry_title: 'Bar these rows'
          }
        }
      }, { wfModuleId: 2 })
      w.find('button.table-action').simulate('click') // open the menu
      expect(w.find('.dropdown-menu').text()).toMatch(/Bar these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(api.addModule).toHaveBeenCalledWith('tab-1', 'step-X', 'dobar', 1, { rows: '2, 4-5' })
    })

    it('should use setWfModuleParams action, fromInput', async () => {
      const w = wrapper({
        workflow: { tab_slugs: ['tab-1'] },
        tabs: { 'tab-1': { wf_module_ids: [2, 3] } },
        wfModules: {
          2: { module: 'dofoo', tab_slug: 'tab-1' },
          3: { module: 'dobaz', tab_slug: 'tab-1', params: { foo20: 'bar20' } }
        },
        modules: {
          dobaz: {
            row_action_menu_entry_title: 'Baz these rows',
            js_module: 'module.exports = { addSelectedRows: (oldParams, rows, fromInput) => ({ oldParams, rows, fromInput }) }'
          }
        }
      }, { wfModuleId: 2 }) // selected module is the input
      w.find('button.table-action').simulate('click') // open the menu
      expect(w.find('.dropdown-menu').text()).toMatch(/Baz these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(api.setSelectedWfModule).toHaveBeenCalledWith(3)
      expect(api.setWfModuleParams).toHaveBeenCalledWith(
        3,
        { oldParams: { foo20: 'bar20' }, rows: '2, 4-5', fromInput: true }
      )
    })

    it('should use setWfModuleParams action, fromInput=false (from output)', async () => {
      const w = wrapper({
        workflow: { tab_slugs: ['tab-1'] },
        tabs: { 'tab-1': { wf_module_ids: [2, 3] } },
        wfModules: {
          2: { module: 'dobaz', tab_slug: 'tab-1', params: { foo10: 'bar10' } },
          3: { module: 'dofoo', tab_slug: 'tab-1' }
        },
        modules: {
          dobaz: {
            row_action_menu_entry_title: 'Baz these rows',
            js_module: 'module.exports = { addSelectedRows: (oldParams, rows, fromInput) => ({ oldParams, rows, fromInput }) }'
          }
        }
      }, { wfModuleId: 2 }) // selected module is what's we're editing
      w.find('button.table-action').simulate('click') // open the menu
      expect(w.find('.dropdown-menu').text()).toMatch(/Baz these rows/)
      w.find('button').at(1).simulate('click')

      await tick() // wait for all promises to settle

      // Check that the reducer did its stuff. We don't test that store.state
      // is changed because the fact these methods were called implies the
      // reducer was invoked correctly.
      expect(api.setWfModuleParams).toHaveBeenCalledWith(
        2,
        { oldParams: { foo10: 'bar10' }, rows: '2, 4-5', fromInput: false }
      )
    })
  })
})
