import React from 'react'
import PropTypes from 'prop-types'
import ModuleStack from './ModuleStack'
import OutputPane from './OutputPane'
import Tabs from './Tabs'

export const WorkflowEditorNavContext = React.createContext()

const WorkflowEditor = React.memo(function WorkflowEditor ({ api }) {
  return (
    <>
      <div className='workflow-columns'>
        <ModuleStack api={api} />
        <OutputPane api={api} />
      </div>

      <Tabs />
    </>
  )
})
export default WorkflowEditor
