/**
 * Contains the Module Library. The Module Library is effectively the place
 * that allows users to browse all the modules in the system that are
 * available to them. Therefore, the server should only send through the
 * modules the users are entitled to, and this class will render those modules
 * accordingly, and allow users to add them to workflows.
 *
 * Note: the current implementation mandates that this library appears vis-à-vis
 * the workflow, and is not an independent component. Perhaps, at some point, it
 * should be, so that newcomers to the system can get an idea as to the modules
 * that are supported – both, those created by us and those created by third
 * parties.
 *
 */

import PropTypes from 'prop-types';
import React from 'react';
import ModuleLibraryClosed from './ModuleLibraryClosed';
import ModuleLibraryOpen from './ModuleLibraryOpen';
import { store, setWfLibraryCollapseAction } from './workflow-reducer'


// Helper to sort modules by category, then name
function compareCategoryName(a,b) {
  if (a.category > b.category) {
    return 1;
  } else if (a.category < b.category) {
    return -1;
  } else if (a.name > b.name) {
    return 1;
  } else if (a.name < b.name) {
    return -1;
  } else {
    return 0;
  }
}

export default class ModuleLibrary extends React.Component {
  constructor(props) {
    super(props);

    // Do we have any modules at all? If not, "Add Data" category starts open
    var workflowEmpty = (!props.workflow.wf_modules || !props.workflow.wf_modules.length);

    this.state = {
      openCategory: (workflowEmpty && this.props.libraryOpen) ? "Add data" : null,
      items: [],
    };
    this.addModule = this.props.addModule.bind(this);
    this.setOpenCategory = this.setOpenCategory.bind(this);
    this.toggleLibrary = this.toggleLibrary.bind(this);
    this.openLibrary = this.openLibrary.bind(this);
    this.updated = this.updated.bind(this);
  }


  /**
   * Queries server for all the available modules for the given credentials.
   * The response that's returned should be a list, where each item has the
   * following properties:
   * - name (e.g. "Paste CSV")
   * - id (e.g. 8)
   * - category (e.g. "Sources")
   * - description (e.g. "Allows users to copy in a CSV from an external source.")
   *
   * Additionally, these properties are optional (and mostly used by modules
   * imported from GitHub, i.e. not the core modules):
   * - icon
   * - source
   * - author
   * - version
   */
  componentWillMount() {
    this.props.api.getModules()
      .then(json => {

        var categories = ['Add data', 'Prepare', 'Edit', 'Analyze', 'Visualize', 'Code', 'Other'];
        var modules = [];

        // Order modules by categories in order above, then alphabetically by name within category
        for (var cat of categories) {
          let catModules = json.filter( (m) => { return m.category == cat; } );
          catModules.sort(compareCategoryName);
          modules = modules.concat(catModules)
        }

        // See if there are any remanining modules, and if there are, add them under Other
        var remainingModules = json.filter( (item) =>
          { return modules.indexOf(item) === -1; });
        remainingModules.sort(compareCategoryName);
        modules = modules.concat(remainingModules);

        this.setState({ items: modules });
      })
  }

  // Categories call this to indicate that they've been opened, so we can close all the rest
  setOpenCategory(name) {
      this.setState({openCategory: name});
  }

  itemClick(event) {
    this.props.addModule(event.target.id);
  }

  updated() {
    this.componentWillMount() // dummy update to force a re-render.
  }

  toggleLibrary() {
    store.dispatch( setWfLibraryCollapseAction(this.props.workflow.id, !this.state.isCollapsed, this.props.isReadOnly) );
  }

  openLibrary() {
    store.dispatch( setWfLibraryCollapseAction(this.props.workflow.id, false, this.props.isReadOnly) );
  }

  // Main render.
  render() {

    if (this.props.libraryOpen && !this.props.isReadOnly) {
      // Outermost div seems necessary to set background color below ImportFromGithub
      return (
        <div>
          <ModuleLibraryOpen
            workflow={this.props.workflow}
            libraryOpen={true}
            api={this.props.api}
            isReadOnly={this.props.isReadOnly}
            items={this.state.items}
            addModule={this.props.addModule}
            dropModule={this.props.dropModule}
            moduleAdded={this.updated}
            toggleLibrary={this.toggleLibrary}
            openCategory={this.state.openCategory}
            setOpenCategory={this.setOpenCategory}
          />
        </div>
      )
    } else {
      return (
        <ModuleLibraryClosed
          libraryOpen={false}
          api={this.props.api}
          isReadOnly={this.props.isReadOnly}
          items={this.state.items}
          addModule={this.props.addModule}
          dropModule={this.props.dropModule}
          moduleAdded={this.updated}
          openLibrary={this.openLibrary}
          openCategory={this.state.openCategory}
          setOpenCategory={this.setOpenCategory}
        />
      )
    }
  }
}

ModuleLibrary.propTypes = {
  addModule:    PropTypes.func.isRequired,
  dropModule:   PropTypes.func.isRequired,
  workflow:     PropTypes.object.isRequired,
  api:          PropTypes.object.isRequired,
  isReadOnly:   PropTypes.bool.isRequired,
  libraryOpen:  PropTypes.bool.isRequired,
};
