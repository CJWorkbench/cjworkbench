import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import File from './File'
import { upload, cancel } from './actions'

const mapDispatchToProps = {
  uploadFile: upload,
  cancelUpload: cancel
}

export default connect(null, mapDispatchToProps)(File)
