import React from 'react'
import PropTypes from 'prop-types'
import TabList from './TabList'
import NewTabPrompt from './NewTabPrompt'
import * as propTypes from '../propTypes'
import { withI18n } from '@lingui/react'
import { t } from '@lingui/macro'

class Tabs extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
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
    this.props.create(this.props.i18n._(
      /* i18n: The tab prefix will be used as the first part of the default name of tabs, i.e. if the tab prefix is 'Tab', the default names can be 'Tab 1', 'Tab 2', etc */
      t('js.WorkflowEditor.Tabs.create.defaultPrefix')`Tab`
    ))
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

export default withI18n()(Tabs)
