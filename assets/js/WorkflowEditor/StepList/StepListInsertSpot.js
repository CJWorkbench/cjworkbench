import PropTypes from 'prop-types'
import ModuleSearch from '../ModuleSearch'
import StepDropSpot from './StepDropSpot'

export default function StepListInsertSpot (props) {
  const { index, tabSlug, isLast, isReadOnly, isLessonHighlight, draggedStep, reorderStep } = props

  if (isReadOnly) {
    return <div className='in-between-steps read-only' />
  }

  const canDrop = draggedStep && draggedStep.index !== index && draggedStep.index !== index - 1

  return (
    <div className='in-between-steps'>
      <ModuleSearch
        index={index}
        tabSlug={tabSlug}
        className={isLast ? 'module-search-last' : 'module-search-in-between'}
        isLessonHighlight={isLessonHighlight}
        isLastAddButton={isLast}
      />
      {canDrop ? (
        <StepDropSpot
          index={index}
          draggedStep={draggedStep}
          reorderStep={reorderStep}
        />
      ) : null}
    </div>
  )
}
StepListInsertSpot.propTypes = {
  index: PropTypes.number.isRequired,
  tabSlug: PropTypes.string.isRequired,
  isLast: PropTypes.bool.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  draggedStep: PropTypes.shape({
    tabSlug: PropTypes.string.isRequired,
    slug: PropTypes.string.isRequired,
    index: PropTypes.number.isRequired
  }), // or null if not dragging
  reorderStep: PropTypes.func.isRequired // func(oldIndex, newIndex) => undefined
}
