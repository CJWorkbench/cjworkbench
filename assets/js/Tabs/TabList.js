import React from 'react'
import PropTypes from 'prop-types'
import Tab from './Tab'

export default class TabList extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      isPending: PropTypes.bool // or undefined
    }).isRequired).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    selectedTabPosition: PropTypes.number.isRequired,
    setName: PropTypes.func.isRequired, // func(tabSlug, name) => undefined
    destroy: PropTypes.func.isRequired, // func(tabSlug) => undefined
    select: PropTypes.func.isRequired, // func(tabSlug) => undefined
    setOrder: PropTypes.func.isRequired, // func(tabSlugs) => undefined
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
      const tabSlugs = tabs.map(t => t.slug)
      tabSlugs.splice(fromIndex, 1)
      tabSlugs.splice(toIndex > fromIndex ? toIndex - 1 : toIndex, 0, fromId)
      this.props.setOrder(tabSlugs)
    }
  }

  render () {
    const { tabs, selectedTabPosition, isReadOnly, setName, select, destroy } = this.props
    const { dragging } = this.state

    return (
      <ul
        className={dragging ? 'dragging' : ''}
        onDragLeave={this.onDragLeave}
      >
        {tabs.map(({ slug, name, isPending }, index) => (
          <Tab
            key={slug}
            index={index}
            slug={slug}
            isPending={isPending}
            isReadOnly={isReadOnly}
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
