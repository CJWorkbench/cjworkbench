import React from 'react'
import PropTypes from 'prop-types'
import DataVersionModal from '../../../WorkflowEditor/DataVersionModal'
import { connect } from 'react-redux'
import { t, Trans } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class DataVersionSelect extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    wfModuleId: PropTypes.number.isRequired,
    currentVersionIndex: PropTypes.number, // or null for no selected version
    nVersions: PropTypes.number.isRequired, // may be 0
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    isDataVersionModalOpen: false
  }

  handleClickOpenModal = () => this.setState({ isDataVersionModalOpen: true })
  handleCloseModal = () => this.setState({ isDataVersionModalOpen: false })

  render () {
    const { wfModuleId, currentVersionIndex, nVersions, isReadOnly, i18n } = this.props
    const { isDataVersionModalOpen } = this.state

    let inner

    if (nVersions === 0) {
      inner = (
        <>
          <div className='label'>
            <Trans id='js.params.Custom.VersionSelect.DataVersionSelect.noVersions.label'>
                Version
            </Trans>
          </div>
          <div className='no-versions'>–</div>
        </>
      )
    } else if (isReadOnly) {
      inner = (
        <div className='read-only'>
          <Trans id='js.params.Custom.VersionSelect.DataVersionSelect.readOnly.label' description='The parameter {0} will be the current version and {nVersions} will be the number of versions'>
            Version {nVersions - currentVersionIndex} of {nVersions}
          </Trans>
        </div>
      )
    } else {
      inner = (
        <>
          <div className='label'>
            <Trans id='js.params.Custom.VersionSelect.DataVersionSelect.selectVersion.label'>
                Version
            </Trans>
          </div>
          <button
            type='button'
            title={i18n._(t('js.params.Custom.VersionSelect.DataVersionSelect.selectVersion.hoverText')`Select version`)}
            onClick={this.handleClickOpenModal}
          >
            <Trans id='js.params.Custom.VersionSelect.DataVersionSelect.versionCount' description='The parameter {0} will be the current version and {nVersions} will be the number of versions'>
              {nVersions - currentVersionIndex} of {nVersions}
            </Trans>
          </button>
          {isDataVersionModalOpen ? (
            <DataVersionModal
              wfModuleId={wfModuleId}
              onClose={this.handleCloseModal}
            />
          ) : null}
        </>
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
)(withI18n()(DataVersionSelect))
