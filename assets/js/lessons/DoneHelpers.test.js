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
