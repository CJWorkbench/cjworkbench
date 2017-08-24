/**
 * A component that holds a collection of modules for a given category. For example, 
 * Category: Source
 * Modules: Load URL, Paste CSV, Twitter
 * 
 * Category: Wrangle
 * Modules: Melt, Select Columns 
 * 
 * Categories should be expandable and collapsible, just like each individual module.
 */

import React from 'react'
import { sortable } from 'react-sortable'
import PropTypes from 'prop-types'
import Module from './Module'
import { Collapse, Button, CardBlock, Card } from 'reactstrap';

var SortableModule = sortable(Module);

var ModulesList = React.createClass({
  render() {
    // defensive coding because otherwise things blow up for some reason. 
    if (!this.props || !this.props.data) {
      console.log("Something's gone terribly wrong, and we don't have any modules to render.")
      return (
        <div className="list"></div>
      )
    }
    var listItems = this.props.data.map(function (item, i) {
      return (
        <SortableModule
          key={item.key}
          description={item.props.description}
          category={item.props.category}
          author={item.props.author}
          items={this.props}
          sortId={item.key}
          outline="list"
          childProps={{
            'data-name': item.key,
            'data-description': item.props.description,
            'data-category': item.props.category,
            'data-id': item.props.id,
            'data-author': item.props.author,
            'addModule': item.props.addModule,
            'workflow': item.props.workflow,
            'icon': item.props.icon,
          }}
        />
      );
    }, this);
    return (
      <div className="list">{listItems}</div>
    )
  }
})

export default class ModuleCategory extends React.Component {
  constructor(props) {
    super(props);
    this.initFields(props);
    // by default, nothing's collapsed. 
    // I don't know how error-handling should work here, 
    // i.e. what should happen if props doesn't have 'name' 
    this.state = {
      key: props.id, // the name of the category 
      modules: props["modules"],  // collection of underlying Module objects. 
      collapsed: props["collapsed"],
    };

    this.toggleCollapse = this.toggleCollapse.bind(this)
  }

  initFields(props) {
    this.key = props['data-name'];
    this.category = props['data-name'];
    this.modules = props['data-modules'];
    this.collapsed = props['collapsed'];
  }

  toggleCollapse() {
    this.setState(oldState => ({
      collapsed: !oldState.collapsed
    }));
  }

  render() {
    var isOpen = !this.state.collapsed;
    
    // Provides margins around opened library category
    var cardClass = isOpen
      ? 'card b-l-gray library-card-category-open'
      : 'card b-l-gray library-card-category-closed'

    var symbol = isOpen 
      ? 'icon-sort-down button-icon ml-3'
      : 'icon-sort-right button-icon ml-3'

    // --- Need a mapping of catergory-to-icon before implementing
    // var icon = 'icon-' + ??? + ' button-icon mr-2';

    var categoryName = this.props["data-name"]; //self-explanatory 
    
    var modules = this.props["data-modules"]; // list of modules within category 

    var contents =  <ModulesList
                      data={modules}
                    />

    return (
      <div className={cardClass}>
        <div className='first-level d-flex align-items-center'>    
          <div className='' onClick={this.toggleCollapse}>
            <span className={symbol}></span> 
            {/* <span className={icon}></span> */}
            <span className='content-3 t-d-gray ml-3'>{categoryName}</span>
          </div>
        </div>
        <div>
          <Collapse className='b-l-gray' isOpen={isOpen}>
            {contents}
          </Collapse> 
        </div>
      </div>
    );
  }
}