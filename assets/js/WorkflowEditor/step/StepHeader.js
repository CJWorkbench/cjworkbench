import React from 'react'
import PropTypes from 'prop-types'

export default class StepHeader extends React.Component {
  constructor (props) {
    super(props)
    this.setModuleRef = this.setModuleRef.bind(this)
  }

  setModuleRef (ref) {
    this.moduleRef = ref
  }

  shouldComponentUpdate (nextProps) {
    // There's almost certainly a better way to do this. This gets the
    // job done but I'm sure there's a standard practice around this.
    return nextProps.moduleName !== this.props.moduleName &&
      nextProps.isSelected !== this.props.isSelected
  }

  render () {
    return (
      <div className='step--placeholder mx-auto' ref={this.setModuleRef}>
        <div className='module-content'>
          <div className='module-card-header'>
            <div className='d-flex justify-content-start align-items-center'>
              <div className={'icon-' + this.props.moduleIcon + ' module-icon t-vl-gray mr-2'} />
              <div className='t-vl-gray module-name'>{this.props.moduleName}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

StepHeader.propTypes = {
  isSelected: PropTypes.bool,
  moduleIcon: PropTypes.string,
  moduleName: PropTypes.string
}
