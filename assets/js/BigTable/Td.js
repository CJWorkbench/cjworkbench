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
    editValue,
    onChange,
    onSubmit,
    onCancel,
    onDoubleClick,
    Component
  } = props
  const setFocusCell = useFocusCellSetter()
  const setRowSelection = useRowSelectionSetter()
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

  const handleBlur = React.useCallback(
    ev => {
      if (editValue === (value === null ? '' : String(value))) {
        onCancel()
      } else {
        onSubmit({ oldValue: value, newValue: editValue })
      }
    },
    [value, editValue, onCancel, onSubmit]
  )

  const handleInputKeyDown = React.useCallback(
    ev => {
      ev.stopPropagation() // Prevent <TBody> from moving focus

      switch (ev.key) {
        case "Escape":
          onCancel()
          break
        case "Enter":
          ev.target.blur()
          break
      }
    },
    [onCancel]
  )

  return (
    <td
      className={`type-${valueType}${focus ? ' focus' : ''}${submitting ? ' submitting' : ''}`}
      onMouseDown={handleMouseDown}
      onDoubleClick={onDoubleClick}
    >
      <Component value={editValue === null ? value : editValue} />
      {editValue !== null && !submitting
        ? <input autoFocus type="text" value={editValue} onChange={onChange} onFocus={handleFocus} onBlur={handleBlur} onKeyDown={handleInputKeyDown} />
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
  onDoubleClick: PropTypes.func, // or undefined
  editValue: PropTypes.string, // or null. When set, onChange+onSubmit+onCancel may be called.
  onSubmit: PropTypes.func.isRequired, // func({ oldValue, newValue }) => undefined; only called when editValue is non-null and different from value
  onCancel: PropTypes.func.isRequired, // func() => undefined; only called when editValue is non-null
  onChange: PropTypes.func.isRequired // func(ev) => undefined; only called when editValue is non-null
}
export default Td
