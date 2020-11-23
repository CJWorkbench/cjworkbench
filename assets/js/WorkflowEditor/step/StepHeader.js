import React from 'react'
import PropTypes from 'prop-types'

export default function StepHeader (props) {
  const { moduleIcon, moduleName } = props
  return (
    <div className='step--placeholder mx-auto'>
      <div className='module-content'>
        <div className='module-card-header'>
          <div className='d-flex justify-content-start align-items-center'>
            <div className={`icon-${moduleIcon} module-icon t-vl-gray mr-2`} />
            <div className='t-vl-gray module-name'>{moduleName}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
StepHeader.propTypes = {
  moduleIcon: PropTypes.string,
  moduleName: PropTypes.string
}
