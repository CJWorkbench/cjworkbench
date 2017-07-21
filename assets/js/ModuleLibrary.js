import PropTypes from 'prop-types';
import React from 'react';
import { Button } from 'reactstrap';
import { sortable } from 'react-sortable';
import ModuleCategory from './ModuleCategory';
import ImportModuleFromGitHub from './ImportModuleFromGitHub';
import Module from './Module';
import ModuleSearch from './ModuleSearch';

var SortableCategories = sortable(ModuleCategory);

var CategoriesList = React.createClass({
  render() {
    var listItems = this.props.data.map(function (item, i) {
      return (
        <SortableCategories
          key={item.key}
          category={item.props.category}
          items={this.props}
          sortId={item.key}
          outline="list"
          childProps={{
            'data-name': item.key, // category
            'data-modules': item.props.modules, // modules in this category 
            'collapsed': true,
          }}
        />
      );
    }, this);
    return (
      <div className="list">{listItems}</div>
    );
  }
});

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
    this.state = {
      items: [], 
      importFromGitHubVisible: false,
    };
    this.addModule = this.props.addModule.bind(this);
    this.workflow = this.props.workflow; 

    this.setImportFromGitHubComponentVisibility = this.setImportFromGitHubComponentVisibility.bind(this);
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
    var _this = this;
    fetch('/api/modules/', { credentials: 'include' })
      .then(response => response.json())
      .then(json => {
        // Sort modules – first by category, then by name
        json.sort((a, b) => {
          if (a.category > b.category)            { return 1; }          else if (a.category < b.category)            { return -1; }          else if (a.name > b.name)            { return 1; }          else if (a.name < b.name)            { return -1; }          else            { return 0; }
        });
        _this.setState({ items: json });
      })
      .catch((error) => {
        console.log('Unable to retrieve modules to construct the Module Library.', error);
      });
  }

  itemClick(event) {
    this.props.addModule(event.target.id);
  }

  /**
   * Sets the visibility of the "Import from GitHub" component.
   */
  setImportFromGitHubComponentVisibility(isVisible) {
    this.setState(oldState => ({
      importFromGitHubVisible: isVisible
    }));
  }


  /**
   * Renders the Module Library, i.e. a collection of <Module Category>, 
   * which in turn is a collection of <Module>. 
   * 
   * This is sorted by the Category name, but we might want to define a 
   * better sorting order. 
   */
  render() {
    // This assumes that the items are already sorted by category, 
    // which does happen in {code: componentDidMount}. So, if someone 
    // changes that, there is a good chance that this will result in 
    // unexpected behaviour. 
    let modules = this.state.items;
    var previousCategory = null;
    var modulesByCategory = [];
    var categories = [];
    for (let item of modules) { // Yes, for...of is ES6 syntax, and yes, it's gross.
      let module = <Module
        key={item.name}
        description={item.description}
        category={item.category}
        author={item.author}
        id={item.id}
        addModule={this.props.addModule}
        workflow={this.props.workflow}
      />;

      if (previousCategory == null) {
        previousCategory = item.category;
      } else if (previousCategory !== item.category) {
        // We should only create the ModuleCategory once we have all modules 
        //for given category. 
        let moduleCategory = <ModuleCategory
          key={previousCategory}
          modules={modulesByCategory}
          />;
        categories.push(moduleCategory);
        modulesByCategory = [];
        previousCategory = item.category;
      }
      modulesByCategory.push(module);
    }

    // the last item / category 
    let moduleCategory = <ModuleCategory
      key={previousCategory}
      modules={modulesByCategory}
      />;
    categories.push(moduleCategory);

    // Import from GitHub component 
    let importFromGitHub = <ImportModuleFromGitHub url="" moduleLibrary={this}/>;

    var display = null; 
    var displayClassName = null;

    if (this.state.importFromGitHubVisible) {
      displayClassName = 'import-module';
      display = importFromGitHub;
    } else {
      displayClassName = 'import-module-button';
      display = <Button className='button-blue' onClick={() =>
        this.setImportFromGitHubComponentVisibility(true)}> 
        Import from GitHub
        </Button>;
    }

    return (
      <div className="module-library">
        <div className="nav-bar">
          <div className="h1">Module Library</div>
          <div className={displayClassName}>
            {display}
          </div>
        </div>
        <CategoriesList
          data={categories}
        />
        </div>

    );
  }
}

ModuleLibrary.propTypes = {
  addModule: PropTypes.func,
  workflow: PropTypes.object,
};
