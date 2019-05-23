import React from 'react'
import PropTypes from 'prop-types'

export default function Module ({ isLessonHighlight, idName, name, description, icon, onClick }) {
  const handleClick = React.useCallback(ev => { ev.preventDefault(); onClick(idName) })

  let className = 'module'
  if (isLessonHighlight) className += ' lesson-highlight'

  return (
    <a href='#' name={idName} onClick={handleClick} className={className}>
      <i className={`icon-${icon}`}/>
      <div className='text'>
        <h4>{name}</h4>
        <p>{description}</p>
      </div>
    </a>
  )
}
Module.propTypes = {
  idName: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  description: PropTypes.string.isRequired,
  icon: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired // func(idName) => undefined
}
