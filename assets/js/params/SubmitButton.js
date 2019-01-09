import React from 'react'
import PropTypes from 'prop-types'

const SubmitButton = ({ name, onClick, disabled }) => {
  return (
    <div className='submit-button'>
      <button
        name={name}
        type='submit'
        disabled={disabled}
      >
        <i className='icon-play' />
      </button>
    </div>
  )
}
SubmitButton.propTypes = {
  name: PropTypes.string.isRequired, // <button name=...>
  disabled: PropTypes.bool.isRequired // true if there is nothing to submit
}

export default SubmitButton
