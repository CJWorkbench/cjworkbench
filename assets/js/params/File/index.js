import { connect } from 'react-redux'
import File from './File'
import { setStepParamsAction } from '../../workflow-reducer'
import { upload, cancel } from './actions'

const mapStateToProps = (state, ownProps) => {
  const { steps } = state
  const step = steps[String(ownProps.stepId)]
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
