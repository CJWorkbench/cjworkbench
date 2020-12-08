import ReactDOM from 'react-dom'
import React from 'react'
import Embed from '../Embed'
import InternationalizedPage from '../i18n/InternationalizedPage'
import setupI18nGlobal from '../i18n/setupI18nGlobal'

setupI18nGlobal()

ReactDOM.render(
  <InternationalizedPage>
    <Embed
      workflow={window.initState.workflow}
      step={window.initState.step}
    />
  </InternationalizedPage>,
  document.getElementById('root')
)
