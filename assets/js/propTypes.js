import PropTypes from 'prop-types'

function validateWorkflowIdString (props, propName, componentName) {
  if (!/^w[a-zA-Z0-9]+$/.test(props[propName])) {
    throw new Error(`Invalid prop '${propName}' supplied to '${componentName}'. Validation failed.`)
  }
}

export default {
  workflowId: PropTypes.oneOfType([PropTypes.number, validateWorkflowIdString])
}
