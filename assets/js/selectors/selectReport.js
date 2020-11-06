import { createSelector } from 'reselect'
import selectOptimisticState from './selectOptimisticState'

function selectWorkflowBlockSlugs (state) {
  return state.workflow.blockSlugs
}

function selectWorkflowTabSlugs (state) {
  return state.workflow.tab_slugs
}

function selectBlocks (state) {
  return state.blocks
}

function selectSteps (state) {
  return state.steps
}

const selectStepsBySlug = createSelector(selectSteps, steps => {
  const ret = {}
  Object.values(steps).forEach(step => {
    ret[step.slug] = step
  })
  return ret
})

function selectTabs (state) {
  return state.tabs
}

function selectModules (state) {
  return state.modules
}

function createSet (values) {
  const set = {}
  values.forEach(v => { set[v] = null })
  return set
}

const selectModulesWithCharts = createSelector(
  selectModules,
  modules => createSet(Object.keys(modules).filter(m => modules[m].has_html_output))
)

const selectTabSteps = createSelector(
  selectWorkflowTabSlugs,
  selectTabs,
  selectSteps,
  (tabSlugs, tabs, steps) => tabSlugs.map(tabSlug => ({
    slug: tabSlug,
    steps: tabs[tabSlug].step_ids.map(stepId => steps[String(stepId)])
  }))
)

function selectOutputStep (id, steps) {
  const step = steps[String(id)]
  return {
    id,
    slug: step.slug,
    outputStatus: step.output_status,
    deltaId: step.cached_render_result_delta_id
  }
}

function selectTab (slug, tabs, steps) {
  const tab = tabs[slug]
  const outputStepId = tab.step_ids.length === 0 ? null : tab.step_ids[tab.step_ids.length - 1]
  const outputStep = outputStepId ? selectOutputStep(outputStepId, steps) : null
  return {
    slug,
    name: tab.name,
    outputStep
  }
}

function selectBlock (slug, { type, ...rest }, tabs, steps, stepsBySlug) {
  switch (type) {
    case 'chart': return { slug, type, step: stepsBySlug[rest.stepSlug] }
    case 'table': return { slug, type, tab: selectTab(rest.tabSlug, tabs, steps) }
    case 'text': return { slug, type, markdown: rest.markdown }
    default: throw new Error('Unknown block type')
  }
}

const selectCustomReport = createSelector(
  selectWorkflowBlockSlugs,
  selectBlocks,
  selectTabs,
  selectSteps,
  selectStepsBySlug,
  (blockSlugs, blocks, tabs, steps, stepsBySlug) => blockSlugs.map(slug => selectBlock(slug, blocks[slug], tabs, steps, stepsBySlug))
)

const selectAutoReport = createSelector(
  selectTabSteps,
  selectModulesWithCharts,
  (tabSteps, wantModules) => tabSteps.flatMap(
    ({ steps }) => steps.filter(step => step.module in wantModules).map(step => ({
      slug: `block-auto-${step.slug}`,
      type: 'chart',
      step
    }))
  )
)

function selectNonOptimisticReport (state) {
  return state.workflow.hasCustomReport ? selectCustomReport(state) : selectAutoReport(state)
}

/**
 * Select the workflow's "Report" from the state.
 *
 * The Report is an Array of `{slug, type, ...rest}`.
 *
 * If `state.workflow.hasCustomReport` is true, we derive from
 * `state.workflow.blockSlugs` and `state.blocks`. Otherwise, we build an
 * "auto-report" that incorporates all chart-producing steps, in order. (This
 * mimics the server-side "auto-report" logic. We copy that code because A. it's
 * user-visible, so it's clearly defined; and B. we can apply optimistic
 * deltas.)
 */
function selectReport (state) {
  const optimisticState = selectOptimisticState(state)
  return selectNonOptimisticReport(optimisticState)
}

export default selectReport
