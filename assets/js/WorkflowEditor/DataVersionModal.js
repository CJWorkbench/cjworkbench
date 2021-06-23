import { PureComponent } from 'react'
import { i18n } from '@lingui/core'
import PropTypes from 'prop-types'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../components/Modal'
import memoize from 'memoize-one'
import { setDataVersionAction } from '../workflow-reducer'
import { connect } from 'react-redux'
import { Trans } from '@lingui/macro'

// Always print as if our time zone is UTC, when testing
// (all other solutions are worse, including env vars and pre-adjusted test data)
let _formatDateUTCforTesting = false
export function formatDateUTCForTesting (bool) {
  _formatDateUTCforTesting = bool
}

/**
 * Form <input type="radio">. Calls onSelect on change.
 */
class FetchVersion extends PureComponent {
  static propTypes = {
    id: PropTypes.string.isRequired, // version ID
    date: PropTypes.instanceOf(Date).isRequired, // version date
    isSelected: PropTypes.bool.isRequired,
    onSelect: PropTypes.func.isRequired // func(versionId) => undefined
  }

  handleChange = ev => {
    if (ev.target.checked) {
      this.props.onSelect(this.props.id)
    }
  }

  render () {
    const { id, date, isSelected } = this.props

    return (
      <label className={isSelected ? 'selected' : ''}>
        <input
          type='radio'
          name='data-version'
          value={id}
          checked={isSelected}
          onChange={this.handleChange}
        />
        <time time={date.toISOString()}>
          {i18n.date(date, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            timeZoneName: 'short',
            hour12: true,
            timeZone: _formatDateUTCforTesting ? 'UTC' : undefined
          })}
        </time>
      </label>
    )
  }
}

export class DataVersionModal extends PureComponent {
  static propTypes = {
    stepId: PropTypes.number.isRequired,
    fetchVersions: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.string.isRequired,
        date: PropTypes.instanceOf(Date).isRequired
      })
    ).isRequired,
    selectedFetchVersionId: PropTypes.string, // null for no selection
    onClose: PropTypes.func.isRequired, // func() => undefined
    onChangeFetchVersionId: PropTypes.func.isRequired // func(stepId, versionId) => undefined
  }

  state = {
    selectedFetchVersionId: this.props.selectedFetchVersionId
  }

  handleSelectSelectedFetchVersionId = selectedFetchVersionId => {
    this.setState({ selectedFetchVersionId })
  }

  handleSubmit = () => {
    if (this.state.selectedFetchVersionId !== this.props.selectedFetchVersionId) {
      const { stepId, onChangeFetchVersionId } = this.props
      onChangeFetchVersionId(stepId, this.state.selectedFetchVersionId)
    }

    this.props.onClose()
  }

  render () {
    const { fetchVersions, onClose } = this.props

    return (
      <Modal className='data-versions-modal' isOpen toggle={onClose}>
        <ModalHeader toggle={onClose}>
          <Trans id='js.WorkflowEditor.DataVersionModal.ModalHeader'>
            Data Versions
          </Trans>
        </ModalHeader>
        <ModalBody>
          <form onSubmit={this.handleSubmit} onCancel={onClose}>
            <ol>
              {fetchVersions.map(v => (
                <li key={v.id}>
                  <FetchVersion
                    onSelect={this.handleSelectSelectedFetchVersionId}
                    isSelected={this.state.selectedFetchVersionId === v.id}
                    {...v}
                  />
                </li>
              ))}
            </ol>
          </form>
        </ModalBody>
        <ModalFooter>
          <div className='actions'>
            <button
              name='load'
              disabled={this.state.selectedFetchVersionId === this.props.selectedFetchVersionId}
              onClick={this.handleSubmit}
            >
              <Trans id='js.WorkflowEditor.DataVersionModal.ModalFooter.actions.loadButton'>
                Load
              </Trans>
            </button>
          </div>
        </ModalFooter>
      </Modal>
    )
  }
}

/**
 * Parse `step.versions.versions` Array of { id, date }.
 *
 * step.versions.versions is an Array of [ dateString ] arrays.
 */
const getFetchVersions = memoize(versions => {
  return versions.map(version => {
    const [id] = version
    return {
      id,
      date: new Date(id)
    }
  })
})

function mapStateToProps (state, { stepId }) {
  const step = state.steps[String(stepId)]

  return {
    fetchVersions: getFetchVersions(step.versions.versions || []),
    selectedFetchVersionId: step.versions.selected
  }
}

const mapDispatchToProps = { onChangeFetchVersionId: setDataVersionAction }

export default connect(mapStateToProps, mapDispatchToProps)(DataVersionModal)
