import React from 'react'
import PropTypes from 'prop-types'

export default class RefineStatus extends React.PureComponent {
  static propTypes = {
    clustererProgress: PropTypes.number, // or null when clustered
    nBinsTotal: PropTypes.number // or null when clustering
  }

  render () {
    const { nBinsTotal } = this.props

    let statusText
    if (nBinsTotal === null) {
      statusText = 'Clustering'
    } else if (nBinsTotal === 1) {
      statusText = '1 cluster found'
    } else {
      statusText = `${nBinsTotal} clusters found`
    }

    return (
      <div className='refine-status'>{statusText}</div>
    )
  }
}
