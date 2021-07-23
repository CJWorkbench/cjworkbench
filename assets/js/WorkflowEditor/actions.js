const EDITOR_SELECT_PANE = 'EDITOR_SELECT_PANE'

export function selectReportPaneAction () {
  return {
    type: EDITOR_SELECT_PANE,
    payload: { pane: 'report' }
  }
}

export function selectDatasetPublisherPaneAction () {
  return {
    type: EDITOR_SELECT_PANE,
    payload: { pane: 'dataset' }
  }
}

function reduceSelectPane (state, action) {
  const { pane } = action.payload
  return {
    ...state,
    selectedPane: { pane }
  }
}

export const reducerFunctions = {
  [EDITOR_SELECT_PANE]: reduceSelectPane
}
