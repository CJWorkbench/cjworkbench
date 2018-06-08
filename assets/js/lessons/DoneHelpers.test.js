import { StateWithHelpers, WorkflowModuleWithHelpers, WorkflowWithHelpers } from './DoneHelpers'

describe('DoneHelpers', () => {
  describe('WorkflowWithHelpers', () => {
    it('should give wfModules', () => {
      const workflow = new WorkflowWithHelpers({
        wf_modules: [
          { module_version: { module: { name: 'Foo' } } },
          { module_version: { module: { name: 'Bar' } } },
        ]
      })

      expect(workflow.wfModules.map(wfm => wfm.moduleName)).toEqual([ 'Foo', 'Bar' ])
    })

    it('should give wfModuleNames', () => {
      const workflow = new WorkflowWithHelpers({
        wf_modules: [
          { module_version: { module: { name: 'Foo' } } },
          { module_version: { module: { name: 'Bar' } } },
        ]
      })

      expect(workflow.wfModuleNames).toEqual([ 'Foo', 'Bar' ])
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
        module_version: { module: { name: 'Foo' } },
        parameter_vals: [
          { parameter_spec: { id_name: 'url' }, value: 'foo' },
          { parameter_spec: { id_name: 'bar' }, value: 'baz' },
        ],
      })
      const parameters = wfModule.parameters
      expect(parameters.get('url')).toEqual('foo')
      expect(parameters.get('bar')).toEqual('baz')
      expect(parameters.get('moo')).toBe(null)
    })

    it('should have null parameters.get() on placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        placeholder: true,
      })
      const parameters = wfModule.parameters
      expect(parameters.get('url')).toBe(null)
      expect(parameters.get('bar')).toBe(null)
      expect(parameters.get('moo')).toBe(null)
    })

    it('should have moduleName even when placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        placeholder: true,
        name: 'Add from URL',
      })
      expect(wfModule.moduleName).toEqual('Add from URL')
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

    it('should have selectedVersion even when placeholder', () => {
      const wfModule = new WorkflowModuleWithHelpers({
        placeholder: true,
        name: 'Add from URL',
      })
      expect(wfModule.selectedVersion).toBe(null)
    })

    it('should have .isEmailUpdates if workflow update is on and email is on', () => {
      const on = new WorkflowModuleWithHelpers({
        auto_update_data: true,
        notifications: true,
      })
      expect(on.isEmailUpdates).toBe(true)

      const off1 = new WorkflowModuleWithHelpers({
        auto_update_data: true,
        notifications: false,
      })
      expect(off1.isEmailUpdates).toBe(false)

      const off2 = new WorkflowModuleWithHelpers({
        auto_update_data: false,
        notifications: true,
      })
      expect(off2.isEmailUpdates).toBe(false)
    })
  })

  describe('StateWithHelpers', () => {
    it('should have a .workflow', () => {
      // take a test that succeeds in WorkflowWithHelpers. It should succeed
      // when we test the same thing in a StateWithHelpers({ workflow: ... }).
      const state = new StateWithHelpers({
        workflow: {
          wf_modules: [
            { module_version: { module: { name: 'Foo' } } },
            { module_version: { module: { name: 'Bar' } } },
          ]
        }
      })

      expect(state.workflow.wfModules.map(wfm => wfm.moduleName)).toEqual([ 'Foo', 'Bar' ])
    })

    it('should have a .selectedWfModule', () => {
      const state = new StateWithHelpers({
        workflow: {
          wf_modules: [
            { id: 2, module_version: { module: { name: 'Foo' } } },
            { id: 3, module_version: { module: { name: 'Bar' } } },
          ],
        },
        selected_wf_module: 3,
      })

      expect(state.selectedWfModule.moduleName).toEqual('Bar')
    })
  })
})
