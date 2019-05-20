import React from 'react'
import PropTypes from 'prop-types'

export default function AllNoneButtons ({ isReadOnly, onClickAll, onClickNone }) {
  return (
    <div className='all-none-buttons'>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-all'
        title='Select All'
        onClick={onClickAll}
      >
        All
      </button>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-none'
        title='Select None'
        onClick={onClickNone}
      >
        None
      </button>
    </div>
  )
}
AllNoneButtons.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  onClickNone: PropTypes.func.isRequired, // func() => undefined
  onClickAll: PropTypes.func.isRequired // func() => undefined
}
