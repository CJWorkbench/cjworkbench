// Helpers for use in a LessonStep's `data-done=` HTML attribute
//
// On-demand, they grok the Redux store's `getState()` in an
// API that we expect will last a long time.
//
// Basically: lessons can't test _everything_ in `getState()`:
// just the things they absolutely need. Hopefully we'll keep
// our lessons' feature set small that way, making for simpler
// lessons and less pain when we refactor global state.

export class StateWithHelpers {
  constructor(state) {
    this.state = state
  }

  get workflow() {
    return new WorkflowWithHelpers(this.state.workflow)
  }

  get selectedWfModule() {
    const id = this.state.selected_wf_module || null
    return this.workflow.wfModules.find(m => m.id === id) || null
  }
}

export class WorkflowWithHelpers {
  constructor(workflow) {
    this.workflow = workflow
  }

  get wfModules() {
    return this.workflow.wf_modules.map(wfm => new WorkflowModuleWithHelpers(wfm))
  }

  get wfModuleNames() {
    return this.wfModules.map(wfm => wfm.moduleName)
  }
}

export class WorkflowModuleWithHelpers {
  constructor(wfModule) {
    this.wfModule = wfModule
  }

  get id() {
    return this.wfModule.id
  }

  get isCollapsed() {
    return this.wfModule.is_collapsed
  }

  get module() {
    return this.moduleVersion ? this.moduleVersion.module : null
  }

  get moduleName() {
    return this.module ? this.module.name : this.wfModule.name
  }

  get moduleVersion() {
    return this.wfModule.module_version
  }

  get note() {
    return this.wfModule.notes
  }

  get parameters() {
    return new ParametersWithHelpers(this.wfModule.parameter_vals || [])
  }
}

export class ParametersWithHelpers {
  constructor(parameters) {
    this.parameters = parameters
  }

  get(key) {
    const p = this.parameters.find(p => p.parameter_spec.id_name === key)
    if (p) {
      return p.value
    } else {
      return null
    }
  }
}
