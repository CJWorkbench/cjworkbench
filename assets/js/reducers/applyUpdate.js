import applyLocalMutations from './applyLocalMutations'

export default function applyUpdate (state, update) {
  let {
    workflow,
    steps,
    tabs,
    blocks,
    selectedPane,
    pendingMutations = []
  } = state

  if (update.updateWorkflow) {
    if (
      selectedPane.pane === 'tab' &&
      update.updateWorkflow.tab_slugs &&
      !update.updateWorkflow.tab_slugs.includes(selectedPane.tabSlug)
    ) {
      // if selectedPane won't point to a valid tab, select a valid one
      // Prefer the tab to the left of the currently-selected tab; fallback
      // (in case of any error we can conceive of) to the first tab.
      const index = workflow.tab_slugs.indexOf(selectedPane.tabSlug)
      selectedPane = {
        pane: 'tab',
        tabSlug: update.updateWorkflow.tab_slugs[Math.max(0, index - 1)]
      }
    }

    workflow = {
      ...workflow,
      ...update.updateWorkflow
    }
  }

  if (update.updateSteps || update.clearStepIds) {
    steps = { ...steps }

    if (update.updateSteps) {
      for (const stepId in update.updateSteps || {}) {
        steps[stepId] = {
          ...steps[stepId],
          ...update.updateSteps[stepId]
        }
      }
    }

    if (update.clearStepIds) {
      steps = { ...steps }
      for (const stepId of update.clearStepIds || []) {
        delete steps[String(stepId)]
      }
    }
  }

  if (update.updateTabs || update.clearTabSlugs) {
    tabs = { ...tabs }

    for (const tabSlug in update.updateTabs || {}) {
      const tabUpdate = update.updateTabs[tabSlug]
      const oldPosition = tabs[tabSlug]
        ? tabs[tabSlug].selected_step_position
        : null
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
    }

    for (const tabSlug of update.clearTabSlugs || []) {
      delete tabs[tabSlug]
    }
  }

  if (update.updateBlocks || update.clearBlockSlugs) {
    blocks = update.updateBlocks
      ? { ...blocks, ...update.updateBlocks }
      : { ...blocks }
    if (update.clearBlockSlugs) {
      update.clearBlockSlugs.forEach(slug => {
        delete blocks[slug]
      })
    }
  }

  if (update.mutationId) {
    pendingMutations = pendingMutations.filter(u => u.id !== update.mutationId)
  }

  return applyLocalMutations({
    ...state,
    tabs,
    workflow,
    steps,
    blocks,
    selectedPane,
    pendingMutations
  })
}
