/* global describe, it, expect */
import { StateWithHelpers, WorkflowModuleWithHelpers, WorkflowWithHelpers } from './DoneHelpers'

describe('DoneHelpers', () => {
  describe('WorkflowWithHelpers', () => {
    it('should give wfModules', () => {
      const workflow = new WorkflowWithHelpers({
        tab_ids: [ 21, 22 ],
        selected_tab_position: 0
      }, {
        tabs: {
          21: { wf_module_ids: [ 1, 2 ] },
          22: { wf_module_ids: [] }
        },
        wfModules: {
          1: { module_version: { module: 12 } },
          2: { module_version: { module: 22 } }
        },
        modules: {
          12: { name: 'Foo' },
          22: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.wfModules.map(wfm => wfm.moduleName)).toEqual([ 'Foo', 'Bar' ])
    })

    it('should give wfModuleNames', () => {
      const workflow = new WorkflowWithHelpers({
        tab_ids: [ 21, 22 ],
        selected_tab_position: 0
      }, {
        tabs: {
          21: { wf_module_ids: [ 1, 2 ] },
          22: { wf_module_ids: [] }
        },
        wfModules: {
          1: { module_version: { module: 12 } },
          2: { module_version: { module: 22 } }
        },
        modules: {
          12: { name: 'Foo' },
          22: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.wfModuleNames).toEqual([ 'Foo', 'Bar' ])
    })

    it('should give wfModuleName=null when there is no module_version', () => {
      const workflow = new WorkflowWithHelpers({
        tab_ids: [ 21, 22 ],
        selected_tab_position: 0
      }, {
        tabs: {
          21: { wf_module_ids: [ 1, "3_nonce" ] },
          22: { wf_module_ids: [] }
        },
        wfModules: {
          1: { module_version: null },
        },
        modules: {}
      })

      expect(workflow.selectedTab.wfModuleNames).toEqual([ null, null ])
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

    it('should have parameters.get()', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        module_version: { module: 123 },
        parameter_vals: [
          { parameter_spec: { id_name: 'url' }, value: 'foo' },
          { parameter_spec: { id_name: 'bar' }, value: 'baz' }
        ]
      }, {
        modules: {
          123: { name: 'Foo' }
        }
      })
      const parameters = wfModule.parameters
      expect(parameters.get('url')).toEqual('foo')
      expect(parameters.get('bar')).toEqual('baz')
      expect(parameters.get('moo')).toBe(null)
    })

    it('should have null parameters.get() on placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers(null, {})
      const parameters = wfModule.parameters
      expect(parameters.get('url')).toBe(null)
      expect(parameters.get('bar')).toBe(null)
      expect(parameters.get('moo')).toBe(null)
    })

    it('should have moduleName=null when placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers(null, { modules: {} })
      expect(wfModule.moduleName).toBe(null)
    })

    it('should have selectedVersion', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        versions: {
          versions: [ [ 'some-sort-of-id', 'why is this an Array?' ] ],
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

    it('should return a concise .updateInterval String', () => {
      const go = (interval, units) => new WorkflowModuleWithHelpers({
        auto_update_data: true,
        update_interval: interval,
        update_units: units
      }).updateInterval

      expect(go(1, 'minutes')).toEqual('1m')
      expect(go(2, 'hours')).toEqual('2h')
      expect(go(3, 'days')).toEqual('3d')
      expect(go(4, 'weeks')).toEqual('4w')
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
          tab_ids: [ 21, 22 ],
          selected_tab_position: 1
        },
        tabs: {
          21: { wf_module_ids: [] },
          22: { wf_module_ids: [ 1, 2 ] },
        },
        wfModules: {
          1: { module_version: { module: 3 } },
          2: { module_version: { module: 4 } }
        },
        modules: {
          3: { name: 'Foo' },
          4: { name: 'Bar' }
        }
      })

      expect(state.selectedTab.wfModuleNames).toEqual([ 'Foo', 'Bar' ])
    })

    it('should have a .selectedWfModule', () => {
      const state = new StateWithHelpers({
        workflow: {
          tab_ids: [ 11, 12 ],
          selected_tab_position: 1,
        },
        tabs: {
          11: { wf_module_ids: [] },
          12: { wf_module_ids: [ 2, 3 ], selected_wf_module_position: 1 }
        },
        wfModules: {
          2: { module_version: { module: 4 } },
          3: { module_version: { module: 5 } }
        },
        modules: {
          4: { name: 'Foo' },
          5: { name: 'Bar' }
        },
      })

      expect(state.selectedWfModule.moduleName).toEqual('Bar')
    })
  })
})
