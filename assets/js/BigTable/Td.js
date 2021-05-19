import React from 'react'
import PropTypes from 'prop-types'
import { FocusCellSetterContext, RowSelectionSetterContext } from './state'

export default function Td (props) {
  const {
    value,
    valueType,
    focus,
    row,
    column,
    Component
  } = props
  const setFocusCell = React.useContext(FocusCellSetterContext)
  const setRowSelection = React.useContext(RowSelectionSetterContext)

  const handleMouseDown = React.useMemo(() => {
    if (!setFocusCell) return undefined
    return ev => {
      if (ev.button === 0) {
        setFocusCell({ row, column })
        setRowSelection(new Uint8Array([]))
      }
    }
  }, [setFocusCell])

  return (
    <td
      className={`type-${valueType}${focus ? ' focus' : ''}`}
      onMouseDown={handleMouseDown}
    >
      <Component value={value} />
    </td>
  )
}
Td.propTypes = {
  value: PropTypes.any, // may be null
  valueType: PropTypes.oneOf(['date', 'number', 'text', 'timestamp']).isRequired,
  focus: PropTypes.bool.isRequired,
  row: PropTypes.number.isRequired,
  column: PropTypes.number.isRequired,
  Component: PropTypes.elementType.isRequired
}
