import ReactDOM from 'react-dom'
import InternationalizedPage from '../i18n/InternationalizedPage'
// import selectWorkflowIdOrSecretId from '../selectors/selectWorkflowIdOrSecretId'
import WorkflowApiPage from '../WorkflowApiPage'

// const workflowIdOrSecretId = selectWorkflowIdOrSecretId(window.initState)

ReactDOM.render(
  <InternationalizedPage>
    <WorkflowApiPage
      loggedInUser={window.initState.loggedInUser}
      workflow={window.initState.workflow}
    />
  </InternationalizedPage>,
  document.querySelector('main')
)
