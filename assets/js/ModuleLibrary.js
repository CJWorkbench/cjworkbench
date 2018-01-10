import PropTypes from 'prop-types';
import React from 'react';
// import ModuleCategory from './ModuleCategory';
import ModuleCategories from './ModuleCategories';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
// import Module from './Module';
import ModuleSearch from './ModuleSearch';
import AddNotificationButton from './AddNotificationButton';


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
      libraryOpen: !this.props.isReadOnly, // TODO: remember this state after exiting
      openCategory: workflowEmpty ? "Add data" : null,
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

          // First, filter out all the core modules, which should be displayed alphabetically.
          var coreModules = json.filter(function(x){
            return x.category == 'Add data' || x.category == 'Analyse' || x.category == 'Visualize';
          });

          // Then, filter out the next set of core modules, also to be displayed alphabetically.
          // ...but, essentially, the thing is, we want 'Code' to appear after 'Visualize', so we have to do this.
          var codeModules = json.filter(function(x){
              return x.category == 'Code' || x.category == 'Other';
          });

          // Add codeModules to coreModules
          codeModules.forEach(function(x) {
              coreModules.push(x);
          });

          // See if there are any remanining modules, and if there are, add them too.
          var remainingModules = json.filter(function (item) {
            return coreModules.indexOf(item) === -1;
          });

          remainingModules.forEach(function(x) {
            coreModules.push(x);
          });

          this.setState({ items: coreModules });
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

  openLibrary() {
    if (!this.props.isReadOnly) {
      this.setState({ libraryOpen: true });
    }
  }


  // Return an array of <Module Category>, each of which has child <Module>s.
  // renderCategories() {
  //   // This assumes that the items are already sorted by category,
  //   // which happens in {code: componentDidMount}. So, if someone
  //   // changes that, there is a good chance that this will result in
  //   // unexpected behaviour.
  //   var modules = this.state.items;
  //   var currentCategory = null;
  //   var modulesByCategory = [];
  //   var categories = [];

  //   for (var item of modules) {

  //     let module = <Module
  //       key={item.name}
  //       name={item.name}
  //       icon={item.icon}
  //       id={item.id}
  //       addModule={this.props.addModule}
  //       dropModule={this.props.dropModule}
  //     />;

  //     if (currentCategory  === null) {
  //       currentCategory  = item.category;
  //     } else if (currentCategory !== item.category) {
  //       // We should only create the ModuleCategory once we have all modules for given category.

  //       // console.log("Creating category " +  currentCategory);

  //       // Start Add Data open if there is nothing in the Workflow
  //       let moduleCategory = <ModuleCategory
  //         name={currentCategory }
  //         key={currentCategory }
  //         modules={modulesByCategory}
  //         isReadOnly={this.props.isReadOnly}
  //         collapsed={currentCategory != this.state.openCategory}
  //         setOpenCategory={this.setOpenCategory}
  //         libraryOpen={this.state.libraryOpen}
  //       />;
  //       categories.push(moduleCategory);
  //       modulesByCategory = [];
  //       currentCategory  = item.category;
  //     }
  //     modulesByCategory.push(module);
  //   }

  //   // the last item / category
  //   if (currentCategory  != null) {  // modules may not be loaded yet
  //     // console.log("Creating final category " +  currentCategory);

  //     let moduleCategory = <ModuleCategory
  //       name={currentCategory }
  //       key={currentCategory }
  //       modules={modulesByCategory}
  //       isReadOnly={this.props.isReadOnly}
  //       collapsed={currentCategory != this.state.openCategory}
  //       setOpenCategory={this.setOpenCategory}
  //       libraryOpen={this.state.libraryOpen}        
  //     />;
  //     categories.push(moduleCategory);
  //   }

  //   return categories;
  // }

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

              <div className='d-flex align-items-center search-bar'>
                <div className='icon-search-white ml-icon-search ml-4'></div>
                <ModuleSearch addModule={this.props.addModule}
                              dropModule={this.props.dropModule}
                              items={this.state.items}
                              workflow={this.props.workflow} />
              </div>

            </div>
{/* 
            <div className="list">
               {this.renderCategories()}
            </div> */}


            <ModuleCategories
              openCategory={this.state.openCategory} // check this
              setOpenCategory={this.setOpenCategory} // check this
              libraryOpen={true}
              isReadOnly={this.props.isReadOnly}            
              addModule={this.props.addModule}
              dropModule={this.props.dropModule}
              items={this.state.items}
            />;


            <div className="ml-divider"></div>

            <AddNotificationButton libraryOpen={true}/>

            <div className="ml-divider"></div>

            <ImportModuleFromGitHub moduleAdded={this.updated} libraryOpen={true}/>
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

          <div className='card' onClick={this.openLibrary}>
            <div className='first-level'>
              <div className='icon-search-white ml-icon-search text-center mt-3'></div>
            </div>
          </div>

          <ModuleCategories
            openCategory={this.state.openCategory} // check this
            setOpenCategory={this.setOpenCategory} // check this
            libraryOpen={false}
            isReadOnly={this.props.isReadOnly}            
            addModule={this.props.addModule}
            dropModule={this.props.dropModule}
            items={this.state.items}
          />;

          <AddNotificationButton libraryOpen={false}/>

          <ImportModuleFromGitHub moduleAdded={this.updated} libraryOpen={false}/>          

        </div>
      )
    }
  }

}

ModuleLibrary.propTypes = {
  addModule: PropTypes.func.isRequired,
  dropModule: PropTypes.func.isRequired,
  workflow:  PropTypes.object.isRequired,
  api:       PropTypes.object.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
};
