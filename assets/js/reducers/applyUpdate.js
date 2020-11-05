export default function applyUpdate (state, update) {
  let { workflow, steps, tabs, blocks, pendingTabs, optimisticUpdates = {} } = state

  if (update.updateWorkflow) {
    workflow = {
      ...workflow,
      ...update.updateWorkflow
    }
  }

  if (update.updateSteps || update.clearStepIds) {
    steps = { ...steps }

    if (update.updateSteps) {
      for (const stepId in (update.updateSteps || {})) {
        steps[stepId] = {
          ...steps[stepId],
          ...update.updateSteps[stepId]
        }
      }
    }

    if (update.clearStepIds) {
      steps = { ...steps }
      for (const stepId of (update.clearStepIds || [])) {
        delete steps[String(stepId)]
      }
    }
  }

  if (update.updateTabs || update.clearTabSlugs) {
    tabs = { ...tabs }
    pendingTabs = { ...(pendingTabs || {}) } // shallow copy

    for (const tabSlug in (update.updateTabs || {})) {
      const tabUpdate = update.updateTabs[tabSlug]
      const oldPosition = tabs[tabSlug] ? tabs[tabSlug].selected_step_position : null
      tabs[tabSlug] = {
        ...tabs[tabSlug],
        ...tabUpdate
      }
      if (oldPosition !== null) {
        // Server updates shouldn't overwrite selected_step_position ...
        // _except_ if the client doesn't actually have a position set (such as
        // when duplicate succeeds and the new tab is one we haven't seen).
        tabs[tabSlug].selected_step_position = oldPosition
      }
      delete pendingTabs[tabSlug] // if it's a pendingTab
    }

    for (const tabSlug of (update.clearTabSlugs || [])) {
      delete tabs[tabSlug]
      delete pendingTabs[tabSlug]
    }
  }

  if (update.updateBlocks || update.clearBlockSlugs) {
    blocks = update.updateBlocks ? { ...blocks, ...update.updateBlocks } : { ...blocks }
    if (update.clearBlockSlugs) {
      update.clearBlockSlugs.forEach(slug => { delete blocks[slug] })
    }
  }

  if (update.optimisticId && optimisticUpdates) {
    optimisticUpdates = optimisticUpdates.filter(u => u.optimisticId !== update.optimisticId)
  }

  return {
    ...state,
    tabs,
    pendingTabs,
    workflow,
    steps,
    blocks,
    optimisticUpdates
  }
}
