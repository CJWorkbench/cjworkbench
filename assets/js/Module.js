/**
 * A component that holds a single module that is then contained within the
 * Module Library.
 * The render function here will drive the "card" of each module within
 * the library.
 */

import React from 'react'
import PropTypes from 'prop-types'
import { CardBlock, Card } from 'reactstrap';

export default class Module extends React.Component {
  constructor(props) {
    super(props);
    this.initFields(props);
    this.state = {
      name: props.key,
      description: props.description,
      category: props.category,
      author: props.author,
    };
    this.itemClick = this.itemClick.bind(this);
    this.addModule = this.props.addModule.bind(this);
    this.workflow = this.props.workflow;
  }

  initFields(props) {
    this.key = props['data-name'];
    this.name = props['data-name'];
    this.description = props['data-description'];
    this.category = props['data-category'];
    this.author = props['data-author'];
    this.id = props['data-id'];
  }

  itemClick(evt) {
    var itemID = evt.target.getAttribute('data-id');
    this.props.addModule(this.props['data-id']);
    this.workflow.toggleModuleLibrary();
  }

  render() {
    var moduleName = this.props['data-name'];
    var icon = 'icon-' + this.props['icon'] + ' module-icon ml-3';

    return (
      // TODO: remove inline styles
      <div className='card' style={{'borderRadius': 0, 'border': 0}}>
        <div className='' onClick={this.itemClick} >
          <div className='second-level d-flex flex-row align-items-center'>
            <div className={icon}></div>
            <div>
              <div className='content-3 t-d-gray ml-3'>{moduleName}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }
}

Module.propTypes = {
  addModule:  PropTypes.func,
  workflow: PropTypes.object,
};
