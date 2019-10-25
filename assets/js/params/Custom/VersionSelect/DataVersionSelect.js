import React from 'react'
import PropTypes from 'prop-types'
import DataVersionModal from '../../../WorkflowEditor/DataVersionModal'
import { connect } from 'react-redux'
import { Trans,t } from '@lingui/macro'
import { withI18n,I18n } from '@lingui/react'


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
          <div className='label'>{ this.props.i18n._(t('workbench.version')`Version`) }</div>
          <div className='no-versions'>–</div>
        </>
      )
    } else if (isReadOnly) {
      inner = (
        <div className='read-only'>{ this.props.i18n._(t('workbench.version')`Version`) } {nVersions - currentVersionIndex} { this.props.i18n._(t('workbenchdataversion.of')`of`) } {nVersions}</div>
      )
    } else {
      inner = (
        <>
          <div className='label'>{ this.props.i18n._(t('workbench.version')`Version`) }</div>
          <button type='button' title={ i18n._(t('workbench.dataversionselect.selectversion')`Select version`) } onClick={this.handleClickOpenModal}>{nVersions - currentVersionIndex} { this.props.i18n._(t('workbenchdataversion.of')`of`) } {nVersions}</button>
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
