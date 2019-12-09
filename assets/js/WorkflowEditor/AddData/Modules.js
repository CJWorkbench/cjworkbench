import React from 'react'
import PropTypes from 'prop-types'
import { ModulePropType } from '../ModuleSearch/PropTypes'
import Module from './Module'
import { Trans } from '@lingui/macro'

export default function Modules ({ modules, addModule, search }) {
  const searchKey = search.trim().toLowerCase()
  const foundModules = modules
    .filter(m => `${m.id_name}\n${m.name}\n${m.description}`.toLowerCase().includes(searchKey))

  if (!foundModules.length) {
    return (
      <div className='modules no-results'>
        <p><Trans id='js.WorkflowEditor.AddData.Modules.noModulesFound'>No data connectors match your search.</Trans></p>
      </div>
    )
  } else {
    return (
      <div className='modules'>
        {foundModules.map(m => <Module key={m.idName} onClick={addModule} {...m} />)}
      </div>
    )
  }
}
Modules.propTypes = {
  addModule: PropTypes.func.isRequired, // func(idName) => undefined
  modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
  search: PropTypes.string.isRequired // filter by search -- may be empty
}
