import React from 'react'
import PropTypes from 'prop-types'

export default class RefineClustererProgress extends React.PureComponent {
  static propTypes = {
    progress: PropTypes.number.isRequired
  }

  render () {
    return (
      <div className='refine-clusterer-progress'>
        <progress value={this.props.progress} />
        <div className='message'>Finding clusters…</div>
      </div>
    )
  }
}
