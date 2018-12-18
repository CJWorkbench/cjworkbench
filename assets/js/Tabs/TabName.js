import React from 'react'
import PropTypes from 'prop-types'
import EditableTabName from './EditableTabName'

export default function TabName ({ name, isEditing, onSelect, onRequestEdit, onSubmitEdit, onCancelEdit }) {
  if (isEditing) {
    return (
      <EditableTabName
        value={name}
        onSubmit={onSubmitEdit}
        onCancel={onCancelEdit}
      />
    )
  } else {
    return (
      <button className='tab-name' onMouseDown={onSelect} onClick={onRequestEdit}>
        {name}
      </button>
    )
  }
}
TabName.propTypes = {
  isEditing: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  onSelect: PropTypes.func.isRequired, // func() => undefined
  onRequestEdit: PropTypes.func.isRequired, // func() => undefined
  onSubmitEdit: PropTypes.func.isRequired, // func(name) => undefined
  onCancelEdit: PropTypes.func.isRequired, // func() => undefined
}
