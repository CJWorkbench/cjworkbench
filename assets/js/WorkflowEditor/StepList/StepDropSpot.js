import React from 'react'
import PropTypes from 'prop-types'
import IconAddcHollow from './../../../icons/addc-hollow.svg'

export default function StepDropSpot (props) {
  const { index, draggedStep, reorderStep } = props
  const [isDragHovering, setDragHovering] = React.useState(false)

  const handleDragOver = React.useCallback(ev => {
    ev.preventDefault() // unlike default, this is a valid drop target
  })
  const handleDragEnter = React.useCallback(ev => {
    setDragHovering(true)
  }, [setDragHovering])
  const handleDragLeave = React.useCallback(ev => {
    setDragHovering(false)
  }, [setDragHovering])
  const handleDrop = React.useCallback(ev => {
    ev.preventDefault() // We want no browser defaults
    const { tabSlug, slug } = draggedStep
    setDragHovering(false) // otherwise, will stay hovering next drag
    reorderStep(tabSlug, slug, index)
  }, [draggedStep, index])

  let className = 'step-drop-spot'
  if (isDragHovering) className += ' is-drag-hovering'
  return (
    <div
      className={className}
      onDragOver={handleDragOver}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className='highlight'>
        <IconAddcHollow />
      </div>
    </div>
  )
}
StepDropSpot.propTypes = {
  index: PropTypes.number.isRequired,
  draggedStep: PropTypes.shape({
    tabSlug: PropTypes.string.isRequired,
    slug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired
  }).isRequired,
  reorderStep: PropTypes.func.isRequired // func(tabSlug, stepSlug, newIndex) => undefined
}
