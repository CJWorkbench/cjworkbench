import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

function selectWorkflowTabSlugs (state) {
  return state.workflow.tab_slugs
}

function selectSteps (state) {
  return state.steps
}

function selectTabs (state) {
  return state.tabs
}

function selectModules (state) {
  return state.modules
}

const selectModulesWithCharts = createSelector(
  selectModules,
  modules => {
    const ret = {}
    Object.keys(modules).forEach(moduleId => {
      const module = modules[moduleId]
      if (modules[moduleId].has_html_output) {
        ret[moduleId] = module.name
      }
    })
    return ret
  }
)

const selectOrderedTabs = createSelector(
  selectWorkflowTabSlugs,
  selectTabs,
  (tabSlugs, tabs) => tabSlugs.map(tabSlug => [tabSlug, tabs[tabSlug]])
)

const selectOrderedTabsWithReportableSteps = createSelector(
  selectOrderedTabs,
  selectSteps,
  selectModulesWithCharts,
  (tabs, steps, modules) => tabs.map(([tabSlug, tab]) => ({
    slug: tabSlug,
    name: tab.name,
    chartSteps: tab.step_ids.map(id => steps[String(id)]).filter(step => step.module in modules).map(step => ({
      slug: step.slug,
      moduleName: modules[step.module]
    }))
  }))
)

/**
 * Select Tabs and their Steps that can be added to a workflow's "Report".
 *
 * The result is an Array of { slug, name, chartSteps }.
 *
 * Within this, chartSteps is an Array of { slug, moduleName }.
 */
export default function selectReportableTabs (state) {
  const optimisticState = selectOptimisticState(state)
  return selectOrderedTabsWithReportableSteps(optimisticState)
}
