/**
* Returns an array of <Module Category> components,
*  each of which has child <Module>, sorted by type.
*
* Currently rendered by <ModuleLibraryClosed> and <ModuleLibraryClosed> components
*
*/

import PropTypes from 'prop-types'
import React from 'react'
import ModuleCategory from './ModuleCategory'
import Module from './Module'

function modulesToCategories(modules) {
  const ret = []
  const keyed = {}

  for (const module of modules) {
    const categoryName = module.category

    let category
    if (keyed.hasOwnProperty(categoryName)) {
      category = keyed[categoryName]
    } else {
      category = keyed[categoryName] = {
        name: categoryName,
        modules: [],
      }
      ret.push(category)
    }

    category.modules.push(module)
  }

  return ret
}

export default class ModuleCategories extends React.Component {
  _renderCategory(category) {
    const { name, modules } = category
    const { isReadOnly, libraryOpen, addModule, dropModule, setOpenCategory } = this.props
    const collapsed = this.props.openCategory !== name

    return (
      <ModuleCategory
        name={name}
        key={name}
        modules={modules}
        isReadOnly={isReadOnly}
        collapsed={collapsed}
        addModule={addModule}
        dropModule={dropModule}
        setOpenCategory={setOpenCategory}
        libraryOpen={libraryOpen}
        />
    )
  }

  render() {
    const categories = modulesToCategories(this.props.modules)
    const categoryComponents = categories.map(c => this._renderCategory(c))

    return <div className="list">{categoryComponents}</div>
  }
}

ModuleCategories.propTypes = {
  openCategory:     PropTypes.string,
  addModule:        PropTypes.func.isRequired,
  dropModule:       PropTypes.func.isRequired,
  modules:          PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    category: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
  })).isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
}
