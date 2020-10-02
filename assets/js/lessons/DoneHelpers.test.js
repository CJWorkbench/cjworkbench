/* global describe, it, expect */
import { StateWithHelpers, WorkflowModuleWithHelpers, WorkflowWithHelpers } from './DoneHelpers'

describe('DoneHelpers', () => {
  describe('WorkflowWithHelpers', () => {
    it('should give steps', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { step_ids: [1, 2] },
          'tab-22': { step_ids: [] }
        },
        steps: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.steps.map(step => step.moduleName)).toEqual(['Foo', 'Bar'])
      expect(workflow.selectedTab.steps.map(step => step.moduleSlug)).toEqual(['foo', 'bar'])
    })

    it('should give stepNames', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { step_ids: [1, 2] },
          'tab-22': { step_ids: [] }
        },
        steps: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.stepNames).toEqual(['Foo', 'Bar'])
    })

    it('should give stepModuleIds', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { step_ids: [1, 2] },
          'tab-22': { step_ids: [] }
        },
        steps: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(workflow.selectedTab.stepModuleIds).toEqual(['foo', 'bar'])
    })

    it('should give stepName=null when there is no module', () => {
      const workflow = new WorkflowWithHelpers({
        tab_slugs: ['tab-21', 'tab-22'],
        selected_tab_position: 0
      }, {
        tabs: {
          'tab-21': { step_ids: [1, 2, '3_nonce'] },
          'tab-22': { step_ids: [] }
        },
        steps: {
          1: { module: 'blah' }, // not a real module
          2: {} // no module
        },
        modules: {}
      })

      expect(workflow.selectedTab.stepNames).toEqual([null, null, null])
      expect(workflow.selectedTab.stepModuleIds).toEqual(['blah', null, null])
    })
  })

  describe('WorkflowModuleWithHelpers', () => {
    it('should have .isCollapsed', () => {
      const step = new WorkflowModuleWithHelpers({
        is_collapsed: false
      })
      expect(step.isCollapsed).toBe(false)
    })

    it('should have .note', () => {
      const step = new WorkflowModuleWithHelpers({
        notes: 'foo'
      })
      expect(step.note).toEqual('foo')
    })

    it('should have params', () => {
      const step = new WorkflowModuleWithHelpers({
        params: { url: 'foo', bar: 'baz' }
      })
      expect(step.params).toEqual({
        url: 'foo',
        bar: 'baz'
      })
    })

    it('should have empty params on placeholder', () => {
      const step = new WorkflowModuleWithHelpers(null, {})
      expect(step.params).toEqual({})
    })

    it('should have secrets', () => {
      const step = new WorkflowModuleWithHelpers({
        secrets: { twitter_credentials: { name: '@hello' } }
      })
      expect(step.secrets).toEqual({
        twitter_credentials: { name: '@hello' }
      })
    })

    it('should have empty secrets on placeholder', () => {
      const step = new WorkflowModuleWithHelpers(null, {})
      expect(step.secrets).toEqual({})
    })

    it('should have moduleName=null and moduleSlug=null when placeholder', () => {
      const step = new WorkflowModuleWithHelpers(null, { modules: {} })
      expect(step.moduleName).toBe(null)
      expect(step.moduleSlug).toBe(null)
    })

    it('should have selectedVersion', () => {
      const step = new WorkflowModuleWithHelpers({
        versions: {
          versions: [['some-sort-of-id', 'why is this an Array?']],
          selected: 'some-sort-of-id'
        }
      })
      expect(step.selectedVersion).toBe('some-sort-of-id')
    })

    it('should have .selectedVersion even when placeholder', () => {
      const step = new WorkflowModuleWithHelpers({
        placeholder: true,
        name: 'Load from URL'
      })
      expect(step.selectedVersion).toBe(null)
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
      const step = new WorkflowModuleWithHelpers({
        last_update_check: '2018-07-27T13:27:02.986129Z'
      })
      expect(step.lastFetchCheckAt).toEqual(new Date(Date.UTC(
        2018, 6, 27, 13, 27, 2, 986
      )))

      const stepWithoutDate = new WorkflowModuleWithHelpers({})
      expect(stepWithoutDate.lastFetchCheckAt).toBe(null)
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
          'tab-21': { step_ids: [] },
          'tab-22': { step_ids: [1, 2] }
        },
        steps: {
          1: { module: 'foo' },
          2: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(state.selectedTab.stepNames).toEqual(['Foo', 'Bar'])
      expect(state.selectedTab.stepModuleIds).toEqual(['foo', 'bar'])
    })

    it('should have a .selectedStep', () => {
      const state = new StateWithHelpers({
        workflow: {
          tab_slugs: ['tab-11', 'tab-12'],
          selected_tab_position: 1
        },
        tabs: {
          'tab-11': { step_ids: [] },
          'tab-12': { step_ids: [2, 3], selected_step_position: 1 }
        },
        steps: {
          2: { module: 'foo' },
          3: { module: 'bar' }
        },
        modules: {
          foo: { name: 'Foo' },
          bar: { name: 'Bar' }
        }
      })

      expect(state.selectedStep.moduleName).toEqual('Bar')
      expect(state.selectedStep.moduleSlug).toEqual('bar')
    })
  })
})
