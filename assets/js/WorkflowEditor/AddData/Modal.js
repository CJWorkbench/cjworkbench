import React from 'react'
import PropTypes from 'prop-types'
import { createSelector } from 'reselect'
import { ModulePropType } from '../ModuleSearch/PropTypes'
import lessonSelector from '../../lessons/lessonSelector'
import { addModuleAction } from '../../workflow-reducer'
import { connect } from 'react-redux'
import Modules from './Modules'
import Search from './Search'

export const Modal = React.memo(function Modal ({ modules, tabSlug, close, addModule }) {
  const onSelectModule = React.useCallback(moduleIdName => addModule(tabSlug, moduleIdName))
  const [ search, setSearch ] = React.useState('')
  const closeIfClickIsOnBackdrop = React.useCallback(ev => {
    if (ev.target.className === 'add-data-modal') close()
  })

  return (
    <div className='add-data-modal' onClick={closeIfClickIsOnBackdrop}>
      <section className='content'>
        <header>
          <h5>CHOOSE A DATA SOURCE</h5>
          <button type='button' class='close' aria-label='Close' title='Close' onClick={close}>×</button>
        </header>
        <div className='body'>
          <Search value={search} onChange={setSearch} />
          <Modules modules={modules} addModule={onSelectModule} search={search} />
        </div>
      </section>
    </div>
  )
})
Modal.propTypes = {
  modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
  close: PropTypes.func.isRequired, // func() => undefined
  addModule: PropTypes.func.isRequired // func(tabSlug, moduleIdName) => undefined
}

const NameCollator = new Intl.Collator()
const getModules = ({ modules }) => modules
const getLoadDataModules = createSelector([ getModules, lessonSelector ], (modules, { testHighlight }) => {
  return Object.values(modules)
    .filter(m => m.loads_data && !m.deprecated)
    .sort((a, b) => NameCollator.compare(a.name, b.name))
    .map(m => ({
      idName: m.id_name,
      isLessonHighlight: testHighlight({ type: 'Module', name: m.name, index: 0 }),
      name: m.name,
      description: m.description,
      icon: m.icon,
      category: m.category
    }))
})

const mapStateToProps = (state) => ({
  modules: getLoadDataModules(state)
})

const mapDispatchToProps = (dispatch) => ({
  addModule: (tabSlug, moduleIdName) => {
    dispatch(addModuleAction(moduleIdName, { tabSlug, index: 0 }, {}))
  }
})

export default connect(mapStateToProps, mapDispatchToProps)(Modal)
