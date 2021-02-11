import { createSelector } from 'reselect'

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

function createSet (values) {
  const set = {}
  values.forEach(v => {
    set[v] = null
  })
  return set
}

const selectModulesWithCharts = createSelector(selectModules, modules =>
  createSet(Object.keys(modules).filter(m => modules[m].has_html_output))
)

const selectTabSteps = createSelector(
  selectWorkflowTabSlugs,
  selectTabs,
  selectSteps,
  (tabSlugs, tabs, steps) =>
    tabSlugs.map(tabSlug => ({
      slug: tabSlug,
      steps: tabs[tabSlug].step_ids.map(stepId => steps[String(stepId)])
    }))
)

export const selectAutoReport = createSelector(
  selectTabSteps,
  selectModulesWithCharts,
  (tabSteps, wantModules) =>
    tabSteps.flatMap(({ steps }) =>
      steps
        .filter(step => step.module in wantModules)
        .map(step => ({
          slug: `block-auto-${step.slug}`,
          type: 'chart',
          step
        }))
    )
)

export default selectAutoReport
