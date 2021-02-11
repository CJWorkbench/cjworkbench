import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import TabList from './TabList'
import NewTabPrompt from './NewTabPrompt'
import * as propTypes from '../propTypes'
import { t } from '@lingui/macro'

export default class Tabs extends PureComponent {
  static propTypes = {
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      isPending: PropTypes.bool // or undefined
    }).isRequired).isRequired,
    selectedPane: propTypes.selectedPane.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    create: PropTypes.func.isRequired, // func(name) => undefined
    setName: PropTypes.func.isRequired, // func(slug, name) => undefined
    destroy: PropTypes.func.isRequired, // func(slug) => undefined
    duplicate: PropTypes.func.isRequired, // func(slug) => undefined
    select: PropTypes.func.isRequired, // func(slug) => undefined
    setOrder: PropTypes.func.isRequired // func(slug) => undefined
  }

  create = () => {
    this.props.create(
      t({
        comment: "The tab prefix will be used as the first part of the default name of tabs, i.e. if the tab prefix is 'Tab', the default names can be 'Tab 1', 'Tab 2', etc",
        id: 'js.WorkflowEditor.Tabs.create.defaultPrefix',
        message: 'Tab'
      })
    )
  }

  render () {
    const { tabs, isReadOnly, selectedPane, setName, select, destroy, duplicate, setOrder } = this.props

    return (
      <div className='tabs'>
        <TabList
          tabs={tabs}
          isReadOnly={isReadOnly}
          selectedPane={selectedPane}
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
