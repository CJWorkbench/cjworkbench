import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import { useDispatch, useSelector } from 'react-redux'
import selectOptimisticState from '../../selectors/selectOptimisticState'
import TabsField from './TabsField'
import { setTabSlugs } from './actions'

/**
 * Mimic Django's slugify() function.
 *
 * ref: https://docs.djangoproject.com/en/3.2/ref/utils/#django.utils.text.slugify
 *
 * This only works for ASCII-friendly scripts: Western Europe, the Americas,
 * Australia and swaths of Africa. Bad for Russia, China, Korea, Japan, etc.
 */
function slugify (value) {
  const normalized = value.normalize('NFKD')
  const ascii = Array.from(normalized).filter(c => c.charCodeAt(0) < 128).join('')
  const parts = [...ascii.toLowerCase().matchAll(/[a-z0-9]+/g)]
  return parts.join('-')
}

function selectTabs (state) {
  const { workflow, tabs } = selectOptimisticState(state)
  const tabsPass1 = workflow.tab_slugs.map(slug => {
    const rawTab = tabs[slug]
    const filename = slugify(rawTab.name)
    const isInDataset = workflow.nextDatasetTabSlugs.includes(slug)
    return {
      slug,
      name: rawTab.name,
      filename,
      isInDataset
    }
  })
  const filenameConflicts = {} // ternary: und=not-seen, false=seen-once, true=conflict!
  tabsPass1.forEach(({ filename, isInDataset }) => {
    if (isInDataset) {
      if (filename in filenameConflicts) {
        filenameConflicts[filename] = true
      } else {
        filenameConflicts[filename] = false
      }
    }
  })
  return tabsPass1.map(tab => ({
    ...tab,
    filenameConflict: filenameConflicts[tab.filename] || false
  }))
}

export default function DatasetPublisherForm (props) {
  const { onClickPublish } = props
  const dispatch = useDispatch()
  const tabs = useSelector(selectTabs)
  const onChangeTabs = React.useCallback(
    slugs => { dispatch(setTabSlugs(slugs)) },
    [dispatch, setTabSlugs]
  )

  return (
    <div className='dataset-publisher-form'>
      <TabsField tabs={tabs} onChange={onChangeTabs} />
      <button
        type='button'
        onClick={onClickPublish}
      >
        <Trans id='js.WorkflowEditor.DatasetPublisher.Form.submit'>Publish</Trans>
      </button>
    </div>
  )
}
DatasetPublisherForm.propTypes = {
  onClickPublish: PropTypes.func.isRequired // func() => undefined
}
