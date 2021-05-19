import React from 'react'
import PropTypes from 'prop-types'
import { useFocusCellSetter, useRowSelectionSetter } from './state'

function handleFocus (ev) {
  ev.target.select()
}

const Td = React.memo(function Td (props) {
  const {
    value,
    valueType,
    focus,
    row,
    column,
    onEdit,
    Component
  } = props
  const setFocusCell = useFocusCellSetter()
  const setRowSelection = useRowSelectionSetter()
  const [editValue, setEditValue] = React.useState(null) // null means, "not editing"
  const [submitting, setSubmitting] = React.useState(false)

  const handleMouseDown = React.useMemo(() => {
    if (!setFocusCell) return undefined
    return ev => {
      if (ev.button === 0) {
        setFocusCell({ row, column })
        setRowSelection(new Uint8Array([]))
      }
    }
  }, [setFocusCell])

  const handleDoubleClick = React.useMemo(() => {
    if (!onEdit) return null
    return ev => { setEditValue(value === null ? '' : String(value)) }
  }, [onEdit, value, setEditValue])

  const handleBlur = React.useCallback(
    ev => {
      if (editValue === (value === null ? '' : String(value))) {
        setEditValue(null) // cancel
      } else {
        onEdit({ row, column, oldValue: value, newValue: editValue })
        // onEdit() will lead to a whole new table being created -- and in that
        // new table, the new value will exist. But _this_ table is immutable! Set
        // submitting=True, to render the interim state.
        setSubmitting(true)
      }
    },
    [onEdit, row, column, value, editValue, setSubmitting, setEditValue]
  )

  const handleChange = React.useCallback(
    ev => setEditValue(ev.target.value),
    [setEditValue]
  )

  const handleInputKeyDown = React.useCallback(
    ev => {
      ev.stopPropagation() // Prevent <TBody> from moving focus

      switch (ev.key) {
        case "Escape":
          setEditValue(null)
          break
        case "Enter":
          ev.target.blur()
          break
      }
    },
    [setEditValue]
  )

  return (
    <td
      className={`type-${valueType}${focus ? ' focus' : ''}${submitting ? ' submitting' : ''}`}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClick}
    >
      <Component value={editValue === null ? value : editValue} />
      {editValue !== null && !submitting
        ? <input autoFocus type="text" value={editValue} onChange={handleChange} onFocus={handleFocus} onBlur={handleBlur} onKeyDown={handleInputKeyDown} />
        : null}
    </td>
  )
})
Td.propTypes = {
  value: PropTypes.any, // may be null
  valueType: PropTypes.oneOf(['date', 'number', 'text', 'timestamp']).isRequired,
  focus: PropTypes.bool.isRequired,
  row: PropTypes.number.isRequired,
  column: PropTypes.number.isRequired,
  Component: PropTypes.elementType.isRequired,
  onEdit: PropTypes.func // func({ row, column, oldValue, newValue }) => undefined, or null
}
export default Td
