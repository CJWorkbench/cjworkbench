/* globals HTMLElement */
import { memo } from 'react'
import PropTypes from 'prop-types'
import Button from './Button'
import Step from '../step/Step'

const AddData = memo(function AddData ({ tabSlug, isLessonHighlight, isReadOnly, step, isZenMode, deleteStep, isSelected, api, setZenMode, paneRef }) {
  if (step) {
    return (
      <Step
        isReadOnly={isReadOnly}
        isZenMode={isZenMode}
        step={step}
        deleteStep={deleteStep}
        inputStep={null}
        isSelected={isSelected}
        isAfterSelected={false}
        isDragging={false}
        api={api}
        index={0}
        setZenMode={setZenMode}
      />
    )
  } else if (isReadOnly) {
    return null
  } else {
    return (
      <div className='add-data'>
        <Button
          tabSlug={tabSlug}
          isLessonHighlight={isLessonHighlight}
          paneRef={paneRef}
        />
      </div>
    )
  }
})
AddData.propTypes = {
  tabSlug: PropTypes.string.isRequired,
  isLessonHighlight: PropTypes.bool.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  step: PropTypes.object, // or null if no Step
  /** <WorkflowEditor/Pane> container, where the dialog will open */
  paneRef: PropTypes.shape({ current: PropTypes.instanceOf(HTMLElement) }).isRequired
}
export default AddData
