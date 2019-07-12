/* global describe, it, expect */
import { StateWithHelpers, WorkflowModuleWithHelpers, WorkflowWithHelpers } from './DoneHelpers'

describe('DoneHelpers', () => {
  describe('WorkflowWithHelpers', () => {
    it('should give wfModules', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { wf_module_ids: [1, 2] },
          'tab-22': { wf_module_ids: [] }
        },
        wfModules: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.wfModules.map(wfm => wfm.moduleName)).toEqual(['Foo', 'Bar'])
    })

    it('should give wfModuleNames', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { wf_module_ids: [1, 2] },
          'tab-22': { wf_module_ids: [] }
        },
        wfModules: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.wfModuleNames).toEqual(['Foo', 'Bar'])
    })

    it('should give wfModuleSlugs', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { wf_module_ids: [1, 2] },
          'tab-22': { wf_module_ids: [] }
        },
        wfModules: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.wfModuleSlugs).toEqual(['foo', 'bar'])
    })

    it('should give wfModuleName=null when there is no module', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { wf_module_ids: [1, 2, '3_nonce'] },
          'tab-22': { wf_module_ids: [] }
        },
        wfModules: {
          1: { module: 'blah' }, // not a real module
          2: {} // no module
        },
        modules: {}
      })

      expect(workflow.selectedTab.wfModuleNames).toEqual([null, null, null])
    })
  })

  describe('WorkflowModuleWithHelpers', () => {
    it('should have .isCollapsed', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        is_collapsed: false
      })
      expect(wfModule.isCollapsed).toBe(false)
    })

    it('should have .note', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        notes: 'foo'
      })
      expect(wfModule.note).toEqual('foo')
    })

    it('should have params', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        params: { url: 'foo', bar: 'baz' }
      })
      expect(wfModule.params).toEqual({
        url: 'foo',
        bar: 'baz'
      })
    })

    it('should have empty params on placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers(null, {})
      expect(wfModule.params).toEqual({})
    })

    it('should have moduleName=null when placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers(null, { modules: {} })
      expect(wfModule.moduleName).toBe(null)
    })

    it('should have selectedVersion', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        versions: {
          versions: [['some-sort-of-id', 'why is this an Array?']],
          selected: 'some-sort-of-id'
        }
      })
      expect(wfModule.selectedVersion).toBe('some-sort-of-id')
    })

    it('should have .selectedVersion even when placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        placeholder: true,
        name: 'Add from URL'
      })
      expect(wfModule.selectedVersion).toBe(null)
    })

    it('should have .updateInterval return `null` if auto_update_data is false', () => {
      expect(new WorkflowModuleWithHelpers({
        auto_update_data: false,
        update_interval: 1,
        update_units: 'days'
      }).updateInterval).toBe(null)
    })

    it('should return updateInterval in seconds', () => {
      const go = (interval) => new WorkflowModuleWithHelpers({
        auto_update_data: true,
        update_interval: interval
      }).updateInterval

      expect(go(10)).toEqual(10)
    })

    it('should have .isEmailUpdates if workflow email is on', () => {
      const on = new WorkflowModuleWithHelpers({
        notifications: true
      })
      expect(on.isEmailUpdates).toBe(true)

      const off1 = new WorkflowModuleWithHelpers({
        notifications: false
      })
      expect(off1.isEmailUpdates).toBe(false)
    })

    it('should have .lastFetchCheckAt', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        last_update_check: '2018-07-27T13:27:02.986129Z'
      })
      expect(wfModule.lastFetchCheckAt).toEqual(new Date(Date.UTC(
        2018, 6, 27, 13, 27, 2, 986
      )))

      const wfModuleWithoutDate = new WorkflowModuleWithHelpers({})
      expect(wfModuleWithoutDate.lastFetchCheckAt).toBe(null)
    })
  })

  describe('StateWithHelpers', () => {
    it('should have a .workflow', () => {
      // take a test that succeeds in WorkflowWithHelpers. It should succeed
      // when we test the same thing in a StateWithHelpers({ workflow: ... }).
      const state = new StateWithHelpers({
        workflow: {
          tab_slugs: ['tab-21', 'tab-22'],
          selected_tab_position: 1
        },
        tabs: {
          'tab-21': { wf_module_ids: [] },
          'tab-22': { wf_module_ids: [1, 2] }
        },
        wfModules: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(state.selectedTab.wfModuleNames).toEqual(['Foo', 'Bar'])
    })

    it('should have a .selectedWfModule', () => {
      const state = new StateWithHelpers({
        workflow: {
          tab_slugs: ['tab-11', 'tab-12'],
          selected_tab_position: 1
        },
        tabs: {
          'tab-11': { wf_module_ids: [] },
          'tab-12': { wf_module_ids: [2, 3], selected_wf_module_position: 1 }
        },
        wfModules: {
          2: { module: 'foo' },
          3: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(state.selectedWfModule.moduleName).toEqual('Bar')
    })
  })
})
