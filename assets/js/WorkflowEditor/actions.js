const EDITOR_SELECT_REPORT_PANE = 'EDITOR_SELECT_REPORT_PANE'

export function selectReportPaneAction () {
  return {
    type: EDITOR_SELECT_REPORT_PANE
  }
}

function reduceSelectReportPanePending (state) {
  return {
    ...state,
    selectedPane: { pane: 'report' }
  }
}

export const reducerFunctions = {
  [EDITOR_SELECT_REPORT_PANE]: reduceSelectReportPanePending
}
