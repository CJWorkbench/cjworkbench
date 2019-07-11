/* globals HTMLElement */
import React from 'react'
import PropTypes from 'prop-types'
import Button from './Button'
import WfModule from '../wfmodule/WfModule'

const AddData = React.memo(function AddData ({ tabSlug, isLessonHighlight, isReadOnly, wfModule, isZenMode, removeModule, isSelected, api, setZenMode, paneRef }) {
  if (wfModule) {
    return (
      <WfModule
        isReadOnly={isReadOnly}
        isZenMode={isZenMode}
        wfModule={wfModule}
        removeModule={removeModule}
        inputWfModule={null}
        isSelected={isSelected}
        isAfterSelected={false}
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
  wfModule: PropTypes.object, // or null if no WfModule
  /** <WorkflowEditor/Pane> container, where the dialog will open */
  paneRef: PropTypes.shape({ current: PropTypes.instanceOf(HTMLElement) }).isRequired
}
export default AddData
