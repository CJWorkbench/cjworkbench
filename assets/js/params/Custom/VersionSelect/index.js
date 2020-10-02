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
    stepId: PropTypes.number.isRequired,
    isStepBusy: PropTypes.bool.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // e.g., "version_select"
    label: PropTypes.string.isRequired // e.g., "Update"
  }

  renderMaybeButton () {
    const { isReadOnly, name, label, isStepBusy } = this.props

    if (isReadOnly) return null

    return (
      <button
        name={name}
        type='submit'
        disabled={isStepBusy}
      >
        {isStepBusy ? <i className='spinner' /> : null}
        {label}
      </button>
    )
  }

  render () {
    const { stepId, isReadOnly } = this.props

    return (
      <div className='version-select'>
        <UpdateFrequencySelect
          stepId={stepId}
          isReadOnly={isReadOnly}
        />
        <div className='version-row'>
          <DataVersionSelect stepId={stepId} />
          {this.renderMaybeButton()}
        </div>
      </div>
    )
  }
}

export function VersionSelectSimpler ({ stepId }) {
  return (
    <div className='version-select-simpler'>
      <DataVersionSelect stepId={stepId} />
    </div>
  )
}
