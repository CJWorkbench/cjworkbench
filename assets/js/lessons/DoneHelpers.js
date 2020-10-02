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

  get selectedTab () {
    return this.workflow.selectedTab
  }

  get selectedStep () {
    return this.selectedTab.selectedStep
  }
}

export class WorkflowWithHelpers {
  constructor (workflow, state) {
    this.workflow = workflow
    this.state = state
  }

  get tabs () {
    const { workflow } = this
    const { tabs } = this.state

    return workflow.tab_slugs.map(tabSlug => {
      return new TabWithHelpers(tabs[tabSlug], this.state)
    })
  }

  get selectedTab () {
    const { workflow } = this
    const { tabs } = this.state
    const tab = tabs[workflow.tab_slugs[workflow.selected_tab_position]]
    if (!tab) throw new Error('No selected tab -- this is always an error')
    return new TabWithHelpers(tab, this.state)
  }

  get selectedStep () {
    return this.selectedTab.selectedStep
  }
}

export class TabWithHelpers {
  constructor (tab, state) {
    this.tab = tab
    this.state = state
  }

  get steps () {
    return this.tab.step_ids.map(stepId => {
      const step = this.state.steps[String(stepId)] || null
      return new WorkflowModuleWithHelpers(step, this.state)
    })
  }

  get stepNames () {
    return this.steps.map(step => step.moduleName)
  }

  get stepModuleIds () {
    return this.steps.map(step => step.moduleSlug)
  }

  get selectedStep () {
    const { steps } = this.state
    const position = this.tab.selected_step_position
    if (position === null || position === undefined) return null

    const step = steps[String(this.tab.step_ids[position])] || null
    return new WorkflowModuleWithHelpers(step, this.state)
  }
}

export class WorkflowModuleWithHelpers {
  constructor (step, state) {
    this.step = step // may be null, if Step is being created
    this.state = state
  }

  get id () {
    if (!this.step) return null
    return this.step.id
  }

  get isCollapsed () {
    if (!this.step) return false
    return this.step.is_collapsed
  }

  get module () {
    if (!this.step) return null
    if (!this.step.module) return null
    return this.state.modules[this.step.module] || null
  }

  get moduleName () {
    const module = this.module
    return module ? module.name : null
  }

  get moduleSlug () {
    if (!this.step) return null
    return this.step.module || null
  }

  get note () {
    if (!this.step) return null
    return this.step.notes
  }

  get params () {
    if (!this.step) return {}
    return this.step.params
  }

  get secrets () {
    if (!this.step) return {}
    return this.step.secrets
  }

  get selectedVersion () {
    if (!this.step) return null
    const versions = this.step.versions
    return (versions && versions.selected) || null
  }

  get isEmailUpdates () {
    if (!this.step) return false
    return !!this.step.notifications
  }

  /**
   * The update interval, in seconds. Null if not auto-update.
   */
  get updateInterval () {
    const step = this.step
    if (!step) return null
    if (!step.auto_update_data) return null

    return step.update_interval
  }

  /**
   * Date the server says is the last time it checked an upstream website.
   */
  get lastFetchCheckAt () {
    if (!this.step) return null
    const s = this.step.last_update_check
    return s ? new Date(s) : null
  }
}
