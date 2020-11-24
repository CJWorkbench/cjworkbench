export const STEP_LIST_REORDER_STEPS = 'STEP_LIST_REORDER_STEPS'

export function createReorderStepsMutation ({ mutationId, tabSlug, slugs }) {
  return {
    type: STEP_LIST_REORDER_STEPS,
    id: mutationId,
    args: { tabSlug, slugs }
  }
}

export function reorderSteps (state, { tabSlug, slugs }) {
  const { steps, tabs } = state
  const tab = tabs[tabSlug]
  if (tab === undefined) {
    return state // tab has gone away
  }

  const stepObjects = tab.step_ids.map(id => steps[String(id)])
  if (stepObjects.some(step => step === undefined)) {
    return state // a step has gone away; server will reject request
  }

  const oldSlugs = stepObjects.map(step => step.slug)
  const stepSlugToId = {}
  stepObjects.forEach(step => { stepSlugToId[step.slug] = step.id })

  if (oldSlugs.join('|') === slugs.join('|')) {
    return state // no-op
  }
  if (oldSlugs.slice().sort().join('|') !== slugs.slice().sort().join('|')) {
    return state // list of valid steps has changed; server will reject request
  }
  return {
    ...state,
    tabs: {
      ...tabs,
      [tabSlug]: {
        ...tab,
        step_ids: slugs.map(slug => stepSlugToId[slug])
      }
    }
  }
}

const mutations = {
  [STEP_LIST_REORDER_STEPS]: reorderSteps
}
export default mutations
