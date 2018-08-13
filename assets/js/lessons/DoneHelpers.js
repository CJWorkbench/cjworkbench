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
  constructor (state) {
    this.state = state
  }

  get workflow () {
    return new WorkflowWithHelpers(this.state.workflow, this.state)
  }

  get selectedWfModule () {
    const index = this.state.selected_wf_module // may be null
    return this.workflow.wfModules[index] || null
  }
}

export class WorkflowWithHelpers {
  constructor (workflow, state) {
    this.workflow = workflow
    this.state = state
  }

  get wfModules () {
    return this.workflow.wf_modules.map(wfmId => {
      return new WorkflowModuleWithHelpers(this.state.wfModules[String(wfmId)], this.state)
    })
  }

  get wfModuleNames () {
    return this.wfModules.map(wfm => wfm.moduleName)
  }
}

export class WorkflowModuleWithHelpers {
  constructor (wfModule, state) {
    this.wfModule = wfModule
    this.state = state
  }

  get id () {
    return this.wfModule.id
  }

  get isCollapsed () {
    return this.wfModule.is_collapsed
  }

  get module () {
    const moduleId = this.moduleVersion ? this.moduleVersion.module : null
    return moduleId ? this.state.modules[String(moduleId)] : null
  }

  get moduleName () {
    return this.module ? this.module.name : this.wfModule.name
  }

  get moduleVersion () {
    return this.wfModule.module_version
  }

  get note () {
    return this.wfModule.notes
  }

  get parameters () {
    return new ParametersWithHelpers(this.wfModule.parameter_vals || [])
  }

  get selectedVersion () {
    const versions = this.wfModule.versions
    return (versions && versions.selected) || null
  }

  get isEmailUpdates () {
    return !!this.wfModule.notifications
  }

  /**
   * The update interval in the form "1w", "3h"; null if not auto-update.
   */
  get updateInterval () {
    const wfModule = this.wfModule
    if (!wfModule.auto_update_data) return null

    const n = String(wfModule.update_interval)
    const s = {
      minutes: 'm',
      hours: 'h',
      days: 'd',
      weeks: 'w'
    }[wfModule.update_units] || '?'

    return n + s
  }

  /**
   * Date the server says is the last time it checked an upstream website.
   */
  get lastFetchCheckAt () {
    const s = this.wfModule.last_update_check
    return s ? new Date(s) : null
  }
}

export class ParametersWithHelpers {
  constructor (parameters) {
    this.parameters = parameters
  }

  get (key) {
    const p = this.parameters.find(p => p.parameter_spec.id_name === key)
    if (p) {
      return p.value
    } else {
      return null
    }
  }
}
