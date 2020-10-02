import React from 'react'
import PropTypes from 'prop-types'
import { createSelector } from 'reselect'
import { ModulePropType } from '../ModuleSearch/PropTypes'
import lessonSelector from '../../lessons/lessonSelector'
import { addStepAction } from '../../workflow-reducer'
import { connect } from 'react-redux'
import Modules from './Modules'
import Search from './Search'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export const Modal = React.memo(function Modal ({ i18n, modules, tabSlug, close, addStep }) {
  const onSelectModule = React.useCallback(moduleIdName => addStep(tabSlug, moduleIdName))
  const [search, setSearch] = React.useState('')

  return (
    <section className='add-data-modal'>
      <header>
        <div className='title'>
          <h5>
            <Trans id='js.WorkflowEditor.AddData.Modal.header.title' description='This should be all-caps for styling reasons'>
              CHOOSE A DATA SOURCE
            </Trans>
          </h5>

          <button type='button' className='close' aria-label='Close' title={i18n._(t('js.WorkflowEditor.AddData.Modal.closeButton.hoverText')`Close`)} onClick={close}>×</button>

        </div>
        <Search value={search} onChange={setSearch} />
      </header>
      <div className='body'>
        <Modules modules={modules} addStep={onSelectModule} search={search} />
      </div>
    </section>
  )
})
Modal.propTypes = {
  modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
  close: PropTypes.func.isRequired, // func() => undefined
  addStep: PropTypes.func.isRequired // func(tabSlug, moduleIdName) => undefined
}

const NameCollator = new Intl.Collator()
const getModules = ({ modules }) => modules
const getLoadDataModules = createSelector([getModules, lessonSelector], (modules, { testHighlight }) => {
  return Object.values(modules)
    .filter(m => m.loads_data && !m.deprecated)
    .sort((a, b) => NameCollator.compare(a.name, b.name))
    .map(m => ({
      idName: m.id_name,
      isLessonHighlight: testHighlight({ type: 'Module', id_name: m.id_name, index: 0 }),
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
  addStep: (tabSlug, moduleIdName) => {
    dispatch(addStepAction(moduleIdName, { tabSlug, index: 0 }, {}))
  }
})

export default connect(mapStateToProps, mapDispatchToProps)(withI18n()(Modal))
