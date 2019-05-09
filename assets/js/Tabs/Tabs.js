import React from 'react'
import PropTypes from 'prop-types'
import TabList from './TabList'
import NewTabPrompt from './NewTabPrompt'

export default class Tabs extends React.PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      isPending: PropTypes.bool // or undefined
    }).isRequired).isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    selectedTabPosition: PropTypes.number.isRequired,
    create: PropTypes.func.isRequired, // func(position, name) => undefined
    setName: PropTypes.func.isRequired, // func(slug, name) => undefined
    destroy: PropTypes.func.isRequired, // func(slug) => undefined
    duplicate: PropTypes.func.isRequired, // func(slug) => undefined
    select: PropTypes.func.isRequired, // func(slug) => undefined
    setOrder: PropTypes.func.isRequired, // func(slug) => undefined
  }

  create = () => {
    this.props.create(this.props.tabs.length, '')
  }

  render () {
    const { tabs, isReadOnly, selectedTabPosition, setName, select, destroy, duplicate, setOrder } = this.props

    return (
      <div className='tabs'>
        <TabList
          tabs={tabs}
          isReadOnly={isReadOnly}
          selectedTabPosition={selectedTabPosition}
          setName={setName}
          destroy={destroy}
          duplicate={duplicate}
          select={select}
          setOrder={setOrder}
        />
        {isReadOnly ? null : (
          <NewTabPrompt
            create={this.create}
          />
        )}
      </div>
    )
  }
}
