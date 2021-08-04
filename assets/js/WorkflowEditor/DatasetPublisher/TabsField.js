import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

function TabRow (props) {
  const { slug, name, filename, filenameConflict, checked, onChange } = props
  const handleChange = React.useCallback(
    (ev) => { onChange(slug, ev.target.checked) },
    [slug, checked]
  )

  const classNames = []
  if (checked) {
    classNames.push('checked')
  }
  if (filenameConflict) {
    classNames.push('error')
  }

  const inputId = `datasetPublisherTab-${slug}`

  const errors = []
  if (!filename) {
    errors.push(
      <div key='emptyFilename'>
        <Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.error.emptyFilename'>
          Empty filename: change this tab's name
        </Trans>
      </div>
    )
  } else if (filenameConflict) {
    errors.push(
      <div key='filenameConflict'>
        <Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.error.filenameConflict'>
          Duplicate filename: change a tab name or uncheck a tab
        </Trans>
      </div>
    )
  }

  return (
    <tr className={classNames.join(' ')}>
      <td className='checkbox'>
        <input
          id={inputId}
          type='checkbox'
          name={`datasetPublisherTab[${slug}]`}
          checked={checked}
          onChange={handleChange}
        />
      </td>
      <td className='tab-name'>
        <label htmlFor={inputId}>
          {name}
        </label>
      </td>
      <td className='filename'>
        <tt>{filename}</tt>
      </td>
      <td className='errors'>
        {errors}
      </td>
    </tr>
  )
}
TabRow.propTypes = {
  slug: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
  filename: PropTypes.string.isRequired, // slugified, no extension -- e.g., "a-file-name"
  filenameConflict: PropTypes.bool.isRequired,
  checked: PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired // func(slug, checked) => undefined
}

export default function TabsField (props) {
  const { tabs, onChange } = props
  const handleChangeTabIncluded = (slug, included) => {
    console.log('actually call handler', tabs.filter(t => t.isInDataset).map(t => t.slug), slug, included)
    const newTabs = tabs
      .filter(tab => tab.slug === slug ? included : tab.isInDataset)
      .map(tab => tab.slug)
    console.log(newTabs)
    onChange(newTabs)
  }

  console.log('TabsField', tabs.filter(t => t.isInDataset).map(t => t.slug))

  return (
    <div className='tabs-field'>
      <label><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.label'>Select tables to publish</Trans></label>
      <table>
        <thead>
          <tr>
            <th className='checkbox' />
            <th className='tab-name'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.TabHeader'>Tab</Trans></th>
            <th className='filename'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.FilenameHeader'>Filename</Trans></th>
            <th className='errors' />
          </tr>
        </thead>
        <tbody>
          {tabs.map(({ slug, name, filename, filenameConflict, isInDataset }) => (
            <TabRow
              key={slug}
              slug={slug}
              name={name}
              filename={filename}
              filenameConflict={filenameConflict}
              checked={isInDataset}
              onChange={handleChangeTabIncluded}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
TabsField.propTypes = {
  tabs: PropTypes.arrayOf(PropTypes.shape({
    slug: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    filename: PropTypes.string.isRequired, // slugified, no extension -- e.g., "a-file-name"
    filenameConflict: PropTypes.bool.isRequired,
    isInDataset: PropTypes.bool.isRequired
  }).isRequired).isRequired,
  onChange: PropTypes.func.isRequired // func([slug1, slug2, ...]) => undefined
}
