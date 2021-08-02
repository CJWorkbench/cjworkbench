export const DATASET_SET_TAB_SLUGS = 'DATASET_SET_TAB_SLUGS'

export function createSetTabSlugsMutation ({ mutationId, tabSlugs }) {
  return { type: DATASET_SET_TAB_SLUGS, id: mutationId, args: { tabSlugs } }
}

export function setTabSlugs (state, args) {
  const { tabSlugs } = args
  return {
    ...state,
    workflow: {
      ...state.workflow,
      nextDatasetTabSlugs: tabSlugs
    }
  }
}

const mutations = {
  [DATASET_SET_TAB_SLUGS]: setTabSlugs
}
export default mutations
