import React from 'react'
import PropTypes from 'prop-types'
import ColumnContextMenu from './ColumnContextMenu'
import ColumnType from '../BigTable/ColumnType'
import { connect } from 'react-redux'
import idxToColumnLetter from '../utils/idxToColumnLetter'
import { updateTableAction } from './UpdateTableAction'

const MinWidthPx = 50 // if too narrow, the dropdown menu button overlaps the previous-column resizer

function preventDefault (ev) {
  ev.preventDefault()
}

function ReorderColumnDropZone (props) {
  const { leftOrRight, index, onDropColumnIndex } = props
  const [draggingOver, setDraggingOver] = React.useState(false)
  const handleDragEnter = React.useCallback(() => setDraggingOver(true), [setDraggingOver])
  const handleDragLeave = React.useCallback(() => setDraggingOver(false), [setDraggingOver])

  const className = `column-reorder-drop-zone align-${leftOrRight}${draggingOver ? ' dragging-over' : ''}`

  const handleDrop = React.useCallback(
    ev => { onDropColumnIndex(index) },
    [onDropColumnIndex, index]
  )

  return (
    <div
      className={className}
      onDragOver={preventDefault /* default is, "disable drop" */}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    />
  )
}
ReorderColumnDropZone.propTypes = {
  leftOrRight: PropTypes.oneOf(['left', 'right']).isRequired,
  index: PropTypes.number.isRequired,
  onDropColumnIndex: PropTypes.func.isRequired // func(index) => undefined
}

function ResizeHandle (props) {
  const { index, onResize } = props
  const [x0, setX0] = React.useState(null) // when set, leftmost viewport X of column

  const handleMouseDown = React.useCallback(
    ev => {
      if (ev.button === 0) {
        setX0(ev.target.closest('th').getBoundingClientRect().x)
        ev.preventDefault() // avoid calling dragstart on .column-letter
      }
    },
    [setX0]
  )

  React.useEffect(() => {
    if (x0 === null) return undefined

    const handleMouseMove = ev => {
      const width = Math.max(MinWidthPx, ev.clientX - x0)
      onResize(index, width)
      ev.stopPropagation()
      ev.preventDefault() // prevent selecting text
    }

    const handleMouseUp = ev => {
      setX0(null)
      ev.stopPropagation()
      ev.preventDefault() // prevent clicking column name to rename it
    }

    document.addEventListener('mousemove', handleMouseMove, true)
    document.addEventListener('mouseup', handleMouseUp, true)
    return () => {
      document.removeEventListener('mousemove', handleMouseMove, true)
      document.removeEventListener('mouseup', handleMouseUp, true)
    }
  }, [x0, setX0, index, onResize])

  return <div className='resize-handle' onMouseDown={handleMouseDown} />
}

export class EditableColumnName extends React.Component {
  static propTypes = {
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    dateUnit: PropTypes.oneOf(['day', 'week', 'month', 'quarter', 'year']), // or null
    onRename: PropTypes.func.isRequired,
    inputRef: PropTypes.shape({
      current: PropTypes.instanceOf(window.HTMLElement)
    }).isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    newName: this.props.columnKey,
    editMode: false
  }

  componentDidUpdate (_, prevState) {
    if (!prevState.editMode && this.state.editMode) {
      const input = this.props.inputRef.current
      if (input) {
        input.focus()
        input.select()
      }
    }
  }

  handleEnterEditMode = () => {
    if (!this.props.isReadOnly) {
      this.setState({ editMode: true })
    }
  }

  exitEditMode () {
    this.setState({ editMode: false })
  }

  handleInputChange = ev => {
    this.setState({ newName: ev.target.value })
  }

  handleInputCommit = () => {
    this.setState({
      editMode: false
    })
    if (this.state.newName !== this.props.columnKey) {
      this.props.onRename({
        prevName: this.props.columnKey,
        newName: this.state.newName
      })
    }
  }

  handleInputBlur = () => {
    this.handleInputCommit()
  }

  handleInputKeyDown = ev => {
    // Changed to keyDown as esc does not fire keyPress
    if (ev.key === 'Enter') {
      this.handleInputCommit()
    } else if (ev.key === 'Escape') {
      this.setState({ newName: this.props.columnKey })
      this.exitEditMode()
    }
  }

  render () {
    const { columnType, dateUnit } = this.props
    const { editMode, newName } = this.state

    return (
      <div className='column-key' onClick={this.handleEnterEditMode}>
        {editMode
          ? (
            <div className='value editing'>
              <input
                name='new-column-key'
                type='prout'
                ref={this.props.inputRef}
                value={this.state.newName}
                onChange={this.handleInputChange}
                onBlur={this.handleInputBlur}
                onKeyDown={this.handleInputKeyDown}
              />
            </div>)
          : <div className='value'>{newName}</div>}
        <div className='column-type'>
          <ColumnType type={columnType} dateUnit={dateUnit} />
        </div>
      </div>
    )
  }
}

// Sort arrows, A-Z letter identifiers
export class ColumnHeader extends React.PureComponent {
  static propTypes = {
    stepId: PropTypes.number,
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    dateUnit: PropTypes.oneOf(['day', 'week', 'month', 'quarter', 'year']), // or null
    isReadOnly: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    onDragStartColumnIndex: PropTypes.func.isRequired, // func(index) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined
    onDropColumnIndex: PropTypes.func.isRequired, // func(from, to) => undefined
    onResize: PropTypes.func.isRequired, // func(index, nPixels) => undefined
    draggingColumnIndex: PropTypes.number, // if set, we are dragging
    dispatchTableAction: PropTypes.func.isRequired // func(stepId, moduleIdName, forceNewModule, params)
  }

  inputRef = React.createRef()

  state = {
    newName: this.props.columnKey
  }

  handleClickAction = (idName, forceNewModule, params) => {
    params = {
      ...params,
      columnKey: this.props.columnKey
    }

    this.props.dispatchTableAction(
      this.props.stepId,
      idName,
      forceNewModule,
      params
    )
  }

  startRename = () => {
    this.inputRef.current.handleEnterEditMode()
  }

  handleRename = ({ prevName, newName }) => {
    this.props.dispatchTableAction(this.props.stepId, 'renamecolumns', false, {
      prevName,
      newName
    })
  }

  handleDragStart = ev => {
    if (this.props.isReadOnly) {
      ev.preventDefault()
      return
    }

    this.props.onDragStartColumnIndex(this.props.index)

    ev.dataTransfer.effectAllowed = ['move']
    ev.dataTransfer.dropEffect = 'move'
    ev.dataTransfer.setData('text/plain', this.props.columnKey)
  }

  render () {
    const {
      columnKey,
      columnType,
      dateUnit,
      index,
      isReadOnly,
      onDropColumnIndex,
      onDragEnd,
      onResize,
      draggingColumnIndex
    } = this.props

    return (
      <>
        {draggingColumnIndex !== null && draggingColumnIndex !== index && draggingColumnIndex !== index - 1
          ? <ReorderColumnDropZone leftOrRight='left' index={index} onDropColumnIndex={onDropColumnIndex} />
          : null}
        <div
          className='column-letter'
          draggable
          onDragStart={this.handleDragStart}
          onDragEnd={onDragEnd}
        >
          {idxToColumnLetter(index)}
        </div>
        <EditableColumnName
          columnKey={columnKey}
          columnType={columnType}
          dateUnit={dateUnit}
          onRename={this.handleRename}
          isReadOnly={isReadOnly}
          inputRef={this.inputRef}
        />
        {isReadOnly || draggingColumnIndex !== null
          ? null
          : (
            <ColumnContextMenu
              columnType={columnType}
              renameColumn={this.startRename}
              onClickAction={this.handleClickAction}
            />)}
        {draggingColumnIndex !== null && draggingColumnIndex !== index && draggingColumnIndex !== index + 1
          ? <ReorderColumnDropZone leftOrRight='right' index={index + 1} onDropColumnIndex={onDropColumnIndex} />
          : <ResizeHandle index={index} onResize={onResize} />}
      </>
    )
  }
}

function mapStateToProps () {
  return {}
}

function mapDispatchToProps (dispatch) {
  return {
    dispatchTableAction: (...args) => dispatch(updateTableAction(...args))
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ColumnHeader)
