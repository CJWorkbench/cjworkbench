import React from 'react'
import PropTypes from 'prop-types'
import RefineBins from './RefineBins'
import RefineClusterer from './RefineClusterer'
import RefineClustererProgress from './RefineClustererProgress'
import RefineStatus from './RefineStatus'
import { Modal, ModalHeader, ModalBody, ModalFooter } from '../../../components/Modal'

export default class RefineModal extends React.PureComponent {
  static propTypes = {
    bucket: PropTypes.object.isRequired, // { "str": Number(count), ... }
    onClose: PropTypes.func.isRequired, // onClose() => undefined
    onSubmit: PropTypes.func.isRequired // onSubmit({ value1: newName1, value2: newName1, ... }) => undefined
  }

  state = {
    // One of clustererProgress or bins is always set; the other is always null
    clustererProgress: 0, // Number from 0 to 1 while clustering
    bins: null // array of { name, isSelected, count, bucket } objects after clustering
  }

  onClustererProgress = (clustererProgress) => {
    this.setState({ clustererProgress, bins: null })
  }

  onClustererComplete = (bins) => {
    bins = bins.map(bin => ({
      ...bin,
      isSelected: true
    }))
    this.setState({ clustererProgress: null, bins })
  }

  setBins = (bins) => {
    this.setState({ clustererProgress: null, bins })
  }

  submit = () => {
    const renames = {}
    for (const bin of this.state.bins) {
      if (bin.isSelected) {
        for (const value in bin.bucket) {
          renames[value] = bin.name
        }
      }
    }
    this.props.onSubmit(renames)
  }

  render () {
    const { bucket, onClose } = this.props
    const { clustererProgress, bins } = this.state

    const nBinsTotal = bins ? bins.length : null
    const nBinsSelected = (bins || []).filter(x => x.isSelected).length
    const canSubmit = nBinsSelected > 0

    return (
      <Modal className='refine-modal' size='lg' isOpen fade={false} toggle={onClose}>
        <ModalHeader toggle={onClose}>CLUSTER</ModalHeader>
        <ModalBody>
          <RefineClusterer
            bucket={bucket}
            onProgress={this.onClustererProgress}
            onComplete={this.onClustererComplete}
          />
          { bins ? <RefineBins bins={bins} onChange={this.setBins} /> : <RefineClustererProgress progress={clustererProgress} /> }
        </ModalBody>
        <ModalFooter>
          <RefineStatus clustererProgress={clustererProgress} nBinsTotal={nBinsTotal} />
          <div className='actions'>
            <button
              type='button'
              name='close'
              className='action-button button-gray'
              onClick={onClose}
            >Cancel</button>
            <button
              name='submit'
              type='button'
              className='action-button button-blue'
              onClick={this.submit}
              disabled={!canSubmit}
            >Merge selected</button>
          </div>
        </ModalFooter>
      </Modal>
    )
  }
}
