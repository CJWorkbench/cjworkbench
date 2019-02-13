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

  get selectedWfModule () {
    return this.selectedTab.selectedWfModule
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

  get selectedWfModule () {
    return this.selectedTab.selectedWfModule
  }
}

export class TabWithHelpers {
  constructor (tab, state) {
    this.tab = tab
    this.state = state
  }

  get wfModules () {
    return this.tab.wf_module_ids.map(wfmId => {
      const wfModule = this.state.wfModules[String(wfmId)] || null
      return new WorkflowModuleWithHelpers(wfModule, this.state)
    })
  }

  get wfModuleNames () {
    return this.wfModules.map(wfm => wfm.moduleName)
  }

  get selectedWfModule () {
    const { wfModules } = this.state
    const position = this.tab.selected_wf_module_position
    if (position === null || position === undefined) return null

    const wfModule = wfModules[String(this.tab.wf_module_ids[position])] || null
    return new WorkflowModuleWithHelpers(wfModule, this.state)
  }
}

export class WorkflowModuleWithHelpers {
  constructor (wfModule, state) {
    this.wfModule = wfModule // may be null, if WfModule is being created
    this.state = state
  }

  get id () {
    if (!this.wfModule) return null
    return this.wfModule.id
  }

  get isCollapsed () {
    if (!this.wfModule) return false
    return this.wfModule.is_collapsed
  }

  get module () {
    if (!this.wfModule) return null
    if (!this.wfModule.module) return null
    return this.state.modules[this.wfModule.module] || null
  }

  get moduleName () {
    const module = this.module
    return module ? module.name : null
  }

  get moduleSlug () {
    const module = this.module
    return module ? module.id_name : null
  }

  get note () {
    if (!this.wfModule) return null
    return this.wfModule.notes
  }

  get params () {
    if (!this.wfModule) return {}
    return this.wfModule.params
  }

  get selectedVersion () {
    if (!this.wfModule) return null
    const versions = this.wfModule.versions
    return (versions && versions.selected) || null
  }

  get isEmailUpdates () {
    if (!this.wfModule) return false
    return !!this.wfModule.notifications
  }

  /**
   * The update interval in the form "1w", "3h"; null if not auto-update.
   */
  get updateInterval () {
    const wfModule = this.wfModule
    if (!wfModule) return null
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
    if (!this.wfModule) return null
    const s = this.wfModule.last_update_check
    return s ? new Date(s) : null
  }
}
