import { connect } from 'react-redux'
import File from './File'
import { setStepParamsAction } from '../../workflow-reducer'
import { upload, cancel } from './actions'
import selectStepsById from '../../selectors/selectStepsById'

const mapStateToProps = (state, ownProps) => {
  const step = selectStepsById(state)[ownProps.stepId] || {}
  return {
    inProgressUpload: step.inProgressUpload || null
  }
}

const mapDispatchToProps = {
  uploadFile: upload,
  cancelUpload: cancel,
  setStepParams: setStepParamsAction
}

export default connect(mapStateToProps, mapDispatchToProps)(File)
