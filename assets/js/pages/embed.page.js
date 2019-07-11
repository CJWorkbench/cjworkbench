import ReactDOM from 'react-dom'
import React from 'react'
import Embed from '../Embed'

ReactDOM.render(
  <Embed
    workflow={window.initState.workflow}
    wf_module={window.initState.wf_module}
  />,
  document.getElementById('root')
)
