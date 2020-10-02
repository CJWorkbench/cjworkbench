import ReactDOM from 'react-dom'
import React from 'react'
import Embed from '../Embed'
import { InternationalizedPage } from '../i18n/InternationalizedPage'

ReactDOM.render(
  <InternationalizedPage>
    <Embed
      workflow={window.initState.workflow}
      step={window.initState.step}
    />
  </InternationalizedPage>,
  document.getElementById('root')
)
