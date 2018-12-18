import React from 'react'
import PropTypes from 'prop-types'
import Tab from './Tab'

export default class TabList extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired,
    selectedTabPosition: PropTypes.number.isRequired,
    setName: PropTypes.func.isRequired, // func(tabId, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabId) => undefined
    select: PropTypes.func.isRequired, // func(tabId) => undefined
    setOrder: PropTypes.func.isRequired, // func(tabIds) => undefined
  }

  state = {
    dragging: null // { fromIndex, toIndex } of dragging state, or `null` if not dragging
  }

  onDragStart = (index) => {
    this.setState({ dragging: { fromIndex: index, toIndex: index } })
  }

  onDragHoverIndex = (index) => {
    const { tabs } = this.props
    const { dragging } = this.state
    if (dragging === null) return

    const { fromIndex, toIndex } = dragging

    if (index !== toIndex) {
      this.setState({
        dragging: {
          fromIndex,
          toIndex: index
        }
      })
    }
  }

  onDragEnd = () => {
    this.setState({ dragging: null })
  }

  onDragLeave = () => {
    const { dragging } = this.state
    if (dragging === null) return

    const { fromIndex, toIndex } = dragging
    this.setState({
      dragging: {
        fromIndex,
        toIndex: fromIndex
      }
    })
  }

  onDrop = () => {
    const { setOrder, tabs } = this.props
    const { dragging } = this.state
    if (!dragging) return

    const { fromIndex, toIndex } = dragging
    if (fromIndex !== toIndex) {
      const tabIds = tabs.map(t => t.id)
      const fromId = tabIds[fromIndex]
      tabIds.splice(fromIndex, 1)
      tabIds.splice(toIndex > fromIndex ? toIndex - 1 : toIndex, 0, fromId)
      this.props.setOrder(tabIds)
    }
  }

  render () {
    const { tabs, selectedTabPosition, setName, select, destroy } = this.props
    const { dragging } = this.state

    return (
      <ul
        className={dragging ? 'dragging' : ''}
        onDragLeave={this.onDragLeave}
      >
        {tabs.map(({ id, name }, index) => (
          <Tab
            key={id}
            index={index}
            id={id}
            isSelected={selectedTabPosition === index}
            name={name}
            setName={setName}
            destroy={destroy}
            select={select}
            dragging={dragging}
            onDragStart={this.onDragStart}
            onDragEnd={this.onDragEnd}
            onDragHoverIndex={this.onDragHoverIndex}
            onDrop={this.onDrop}
          />
        ))}
      </ul>
    )
  }
}
