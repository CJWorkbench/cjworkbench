import React from 'react'
import PropTypes from 'prop-types'
import DataVersionSelect from './DataVersionSelect'
import UpdateFrequencySelect from './UpdateFrequencySelect'

/**
 * An UpdateFrequencySelect, DataVersionSelect, and button.
 */
export default class VersionSelect extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number.isRequired,
    wfModuleStatus: PropTypes.oneOf(['ready', 'busy', 'error']).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    onSubmit: PropTypes.func.isRequired, // onSubmit() => undefined
    name: PropTypes.string.isRequired // e.g., "Update"
  }

  renderUpdateFrequencySelect () {
    const { wfModuleId, isReadOnly } = this.props

    return (
      <UpdateFrequencySelect
        wfModuleId={wfModuleId}
        isReadOnly={isReadOnly}
      />
    )
  }

  renderDataVersionSelect () {
    const { wfModuleId } = this.props
    return <DataVersionSelect wfModuleId={wfModuleId} />
  }

  renderMaybeButton () {
    const { isReadOnly, onSubmit, name, wfModuleStatus } = this.props

    if (isReadOnly) return null

    const isBusy = wfModuleStatus === 'busy'

    return (
      <button
        name='fetch'
        onClick={onSubmit}
        disabled={isBusy}
      >
        {isBusy ? <i className="spinner" /> : null}
        {name}
      </button>
    )
  }

  render () {
    const { wfModuleId, isReadOnly, onSubmit, name, wfModuleStatus } = this.props

    return (
      <React.Fragment>
        {this.renderUpdateFrequencySelect()}
        <div className="d-flex justify-content-between mt-2">
          {this.renderDataVersionSelect()}
          {this.renderMaybeButton()}
        </div>
      </React.Fragment>
    )
  }
}
