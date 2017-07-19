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
    this.id = props['data-id'];
  }

  itemClick(evt) {
    var itemID = evt.target.getAttribute('data-id');
    this.props.addModule(this.props['data-id']);
    this.workflow.toggleModuleLibrary();
  }

  render() {
    var moduleName = this.props['data-name']; // name of module 
    var description = this.props['data-description'];

    return (
      <div className='container'>
        <div className='card'>
          <div className='card-block p-1 module-card-wrapper'>
            <div className='module-card-info pl-2 pr-2'>
              <div 
                className='module-card-header mb-2 pt-2 '
                onClick={this.itemClick}
              > 
                <div className='second-level'>
                  <div className='h1'>{moduleName}</div>
                  <div className='p'>{description}</div>
                </div>
              </div>
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