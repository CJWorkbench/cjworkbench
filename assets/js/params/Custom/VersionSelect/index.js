import React from 'react'
import PropTypes from 'prop-types'
import DataVersionSelect from './DataVersionSelect'
import UpdateFrequencySelect from './UpdateFrequencySelect'

/**
 * An UpdateFrequencySelect, DataVersionSelect, and button.
 *
 * The button has type=submit: when the user clicks it, the parent form's
 * onSubmit() will be called.
 */
export default class VersionSelect extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number.isRequired,
    isWfModuleBusy: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // e.g., "version_select"
    label: PropTypes.string.isRequired // e.g., "Update"
  }

  renderMaybeButton () {
    const { isReadOnly, name, label, isWfModuleBusy } = this.props

    if (isReadOnly) return null

    return (
      <button
        name={name}
        type='submit'
        disabled={isWfModuleBusy}
      >
        {isWfModuleBusy ? <i className='spinner' /> : null}
        {label}
      </button>
    )
  }

  render () {
    const { wfModuleId, isReadOnly } = this.props

    return (
      <div className='version-select'>
        <UpdateFrequencySelect
          wfModuleId={wfModuleId}
          isReadOnly={isReadOnly}
        />
        <div className='version-row'>
          <DataVersionSelect wfModuleId={wfModuleId} />
          {this.renderMaybeButton()}
        </div>
      </div>
    )
  }
}

export function VersionSelectSimpler ({ wfModuleId }) {
  return (
    <div className='version-select-simpler'>
      <DataVersionSelect wfModuleId={wfModuleId} />
    </div>
  )
}
