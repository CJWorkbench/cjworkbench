import React from 'react'
import PropTypes from 'prop-types'
import DataVersionModal from '../../../WorkflowEditor/DataVersionModal'
import { connect } from 'react-redux'

export class DataVersionSelect extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number.isRequired,
    currentVersionIndex: PropTypes.number, // or null for no selected version
    nVersions: PropTypes.number.isRequired, // may be 0
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    isDataVersionModalOpen: false
  }

  openModal = () => this.setState({ isDataVersionModalOpen: true })

  closeModal = () => this.setState({ isDataVersionModalOpen: false })

  render () {
    const { wfModuleId, currentVersionIndex, nVersions, isReadOnly } = this.props
    const { isDataVersionModalOpen } = this.state

    let inner

    if (nVersions === 0) {
      inner = (
        <React.Fragment>
          <div className='label'>Version</div>
          <div className='no-versions'>–</div>
        </React.Fragment>
      )
    } else if (isReadOnly) {
      inner = (
        <div className='read-only'>Version {nVersions - currentVersionIndex} of {nVersions}</div>
      )
    } else {
      inner = (
        <React.Fragment>
          <div className='label'>Version</div>
          <button type='button' title='Select version' onClick={this.openModal}>{nVersions - currentVersionIndex} of {nVersions}</button>
          { isDataVersionModalOpen ? (
            <DataVersionModal
              wfModuleId={wfModuleId}
              onClose={this.closeModal}
            />
          ) : null}
        </React.Fragment>
      )
    }

    return (
      <div className='version-item'>
        {inner}
      </div>
    )
  }
}

function mapStateToProps (state, { wfModuleId }) {
  const isReadOnly = state.workflow.read_only

  const wfModule = state.wfModules[String(wfModuleId)]
  if (!wfModule || !wfModule.versions || !wfModule.versions.selected) {
    return {
      currentVersionIndex: null,
      nVersions: 0,
      isReadOnly
    }
  }

  const { versions, selected } = wfModule.versions
  const index = versions.findIndex(arr => arr[0] === selected) || null

  return {
    currentVersionIndex: index,
    nVersions: versions.length,
    isReadOnly
  }
}

export default connect(
  mapStateToProps
)(DataVersionSelect)
