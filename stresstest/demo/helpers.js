const InitStateRegex = /<script[^>]*>\s*window\.initState\s*=\s*(.*?\});/

function loadVarsFromWorkflowHtml (requestParams, response, context, ee, next) {
  const initStateJson = InitStateRegex.exec(response.body)[1]
  const initState = JSON.parse(initStateJson)

  Object.assign(context.vars, {
    WorkflowId: initState.workflow.id,
    Revision: initState.workflow.revision
  })

  for (const wfModuleId of initState.workflow.wf_modules) {
    const wfModule = initState.wfModules[String(wfModuleId)]
    const moduleName = wfModule.module_version.module.id_name
    const varName = {
      'loadurl': 'LoadUrlId',
      'filter': 'FilterId',
      'sort-from-table': 'SortFromTableId',
      'columnchart': 'ColumnChartId'
    }[moduleName]
    context.vars[varName] = wfModuleId

    if (moduleName === 'sort-from-table') {
      context.vars.SortColumnParamId = wfModule.parameter_vals.find(v => v.parameter_spec.id_name === 'column').id
    }
  }

  next()
}

module.exports = {
  loadVarsFromWorkflowHtml
}
