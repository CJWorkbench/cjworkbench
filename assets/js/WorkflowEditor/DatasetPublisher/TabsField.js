import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

function TabRow (props) {
  const { slug, name, filename, filenameConflict, checked, onChange } = props
  const handleChange = React.useCallback(
    () => { onChange(slug, !checked) },
    [slug, checked]
  )

  const inputId = `datasetPublisherTab-${slug}`

  return (
    <tr className={filenameConflict ? 'error' : ''}>
      <td className='tab-name'>{name}</td>
      <td className='include'>
        <div className='toggle'>
          <input
            id={inputId}
            type='checkbox'
            name={`datasetPublisherTab[${slug}]`}
            checked={checked}
            onChange={handleChange}
          />
          <label htmlFor={inputId} />
        </div>
      </td>
      <td className='filename'>
        <tt>{filename}</tt>
        {filenameConflict ? <span className='error'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.error.filenameConflict'>Duplicate filename: uncheck or rename a tab</Trans></span> : null}
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
  const handleChangeTabIncluded = React.useCallback(
    (slug, included) => {
      onChange(
        tabs
          .filter(tab => tab.slug === slug ? included : tab.isInDataset)
          .map(tab => tab.slug)
      )
    },
    [tabs, onChange]
  )

  return (
    <table className='include-tabs'>
      <thead>
        <tr>
          <th className='tab-name'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.TabHeader'>Tab</Trans></th>
          <th className='include'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.IncludeHeader'>Include?</Trans></th>
          <th className='filename'><Trans id='js.WorkflowEditor.DatasetPublisher.TabsField.FilenameHeader'>Filename</Trans></th>
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
