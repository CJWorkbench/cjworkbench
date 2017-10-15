import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategory from './ModuleCategory';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import Module from './Module';
import ModuleSearch from './ModuleSearch';


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
 */
export default class ModuleLibrary extends React.Component {
  constructor(props) {
    super(props);

    // Do we have any modules at all? If not, "Add Data" category starts open
    var workflowEmpty = (!props.workflow.wf_modules || !props.workflow.wf_modules.length);

    this.state = {
      libraryOpen: !this.props.isReadOnly,
      openCategory: workflowEmpty ? "Add data" : null,
      items: [],
    };
    this.addModule = this.props.addModule.bind(this);
    this.setOpenCategory = this.setOpenCategory.bind(this);
    this.toggleLibrary = this.toggleLibrary.bind(this);
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
    if (!this.props.isReadOnly) { // don't load modules if we can't open library
      this.props.api.getModules()
        .then(json => {
          // Sort modules – first by category, then by name
          json.sort((a, b) => {
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
          });
          this.setState({items: json});
        })
    }
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
    if (!this.props.isReadOnly) {
      this.setState({ libraryOpen: !this.state.libraryOpen });
    }
  }

  // Return an array of <Module Category>, each of which has child <Module>s.
  renderCategories() {
    // This assumes that the items are already sorted by category,
    // which happens in {code: componentDidMount}. So, if someone
    // changes that, there is a good chance that this will result in
    // unexpected behaviour.
    var modules = this.state.items;
    var currentCategory = null;
    var modulesByCategory = [];
    var categories = [];

    for (var item of modules) { // Yes, for...of is ES6 syntax, and yes, it's gross.

      let module = <Module
        key={item.name}
        name={item.name}
        icon={item.icon}
        id={item.id}
        addModule={this.props.addModule}
      />;

      if (currentCategory  === null) {
        currentCategory  = item.category;
      } else if (currentCategory !== item.category) {
        // We should only create the ModuleCategory once we have all modules for given category.

        // console.log("Creating category " +  currentCategory);

        // Start Add Data open if there is nothing in the Workflow
        let moduleCategory = <ModuleCategory
          name={currentCategory }
          key={currentCategory }
          modules={modulesByCategory}
          isReadOnly={this.props.isReadOnly}
          collapsed={currentCategory != this.state.openCategory}
          setOpenCategory={this.setOpenCategory}
        />;
        categories.push(moduleCategory);
        modulesByCategory = [];
        currentCategory  = item.category;
      }
      modulesByCategory.push(module);
    }

    // the last item / category
    if (currentCategory  != null) {  // modules may not be loaded yet
      // console.log("Creating final category " +  currentCategory);

      let moduleCategory = <ModuleCategory
        name={currentCategory }
        key={currentCategory }
        modules={modulesByCategory}
        isReadOnly={this.props.isReadOnly}
        collapsed={currentCategory != this.state.openCategory}
        setOpenCategory={this.setOpenCategory}
      />;
      categories.push(moduleCategory);
    }

    return categories;
  }

  // Main render.
  render() {

    // console.log("render...");

    if (this.state.libraryOpen) {
      // Outermost div seems necessary to set background color below ImportFromGithub
      return (
        <div>
          <div className='module-library-open'>
            <div className='library-nav-bar'>

              <div className='d-flex align-items-center flex-row mb-4'>
                <a href="/workflows" className="logo"><img src="/static/images/logo.png" width="20"/></a>
                <a href="/workflows" className='logo-2 ml-3 t-vl-gray '>Workbench</a>
                <div className='icon-sort-left-vl-gray ml-auto mt-2 close-open-toggle' onClick={this.toggleLibrary}></div>
              </div>

              <ModuleSearch addModule={this.props.addModule}
                            items={this.state.items}
                            workflow={this.props.workflow}/>
            </div>

            <div className="list">
              {this.renderCategories()}
            </div>

            <ImportModuleFromGitHub moduleAdded={this.updated}/>
          </div>
        </div>
      )
    } else {
      return (
        <div className='module-library-collapsed'>
          <div className="expand-lib">
            <div className="expand-lib-button d-flex">
              <div className="logo" onClick={this.toggleLibrary}><img src="/static/images/logo.png" width="20"/></div>
              {
                (this.props.isReadOnly)
                  ? null
                  : <div
                      className='icon-sort-right-vl-gray ml-auto ml-3 mt-2 close-open-toggle'
                      onClick={this.toggleLibrary}>
                    </div>
              }
            </div>
          </div>
        </div>
      )
    }
  }

}

ModuleLibrary.propTypes = {
  addModule: PropTypes.func.isRequired,
  workflow:  PropTypes.object.isRequired,
  api:       PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
};
