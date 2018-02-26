/**
* Returns an array of <Module Category> components, 
*  each of which has child <Module>, sorted by type.
* 
* Currently rendered by <ModuleLibraryClosed> and <ModuleLibraryClosed> components
*
*/

import PropTypes from 'prop-types';
import React from 'react';
import ModuleCategory from './ModuleCategory';
import Module from './Module';


export default class ModuleCategories extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      categories: [],
    };
    this.renderCategories = this.renderCategories.bind(this);
  }

  componentWillMount() {
    this.renderCategories();
  }

  componentWillReceiveProps(newProps) {
    this.renderCategories(newProps);
  }

  renderCategories(newProps) {
    var properties = (newProps) ? newProps : this.props;

    var modules = properties.items;
    var currentCategory = null;
    var modulesByCategory = [];
    var categories = [];

    for (var item of modules) {

      let module = <Module
        key={item.name}
        name={item.name}
        icon={item.icon}
        id={item.id}
        addModule={properties.addModule}
        dropModule={properties.dropModule}
        isReadOnly={properties.isReadOnly} 
        setOpenCategory={properties.setOpenCategory}
        libraryOpen={properties.libraryOpen}                                
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
          isReadOnly={properties.isReadOnly}
          collapsed={currentCategory != properties.openCategory} 
          setOpenCategory={properties.setOpenCategory} 
          libraryOpen={properties.libraryOpen}
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
        isReadOnly={properties.isReadOnly}
        collapsed={currentCategory != properties.openCategory} 
        setOpenCategory={properties.setOpenCategory} 
        libraryOpen={properties.libraryOpen}        
      />;
      categories.push(moduleCategory);
    }

    this.setState({ categories });
  }

  render() {
    var categories = this.state.categories;

    return (
      <div className="list">
        {categories}
      </div>
    )
  }
}

ModuleCategories.propTypes = {
  openCategory:     PropTypes.string,
  addModule:        PropTypes.func.isRequired,
  dropModule:       PropTypes.func.isRequired,
  items:            PropTypes.array.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired
};