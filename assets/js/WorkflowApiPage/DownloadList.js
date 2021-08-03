import React from 'react'
import PropTypes from 'prop-types'

function gatherTables (resources) {
  const names = []
  const byName = {}

  resources.forEach(resource => {
    const name = resource.name.replace(/_(csv|json)$/, '')
    if (!(name in byName)) {
      names.push(name)
      byName[name] = {
        name,
        title: resource.title,
        paths: {}
      }
    }
    byName[name].paths[resource.format] = {
      href: resource.path,
      bytes: resource.bytes
    }
  })

  names.sort((a, b) => a.localeCompare(b))
  return names.map(name => byName[name])
}

function formatNBytes (bytes) {
  // https://tc39.es/ecma402/#table-sanctioned-simple-unit-identifiers
  let n, unit
  if (bytes > 512 * 1024 * 1024) { // >= 0.5GB
    unit = 'gigabyte'
    n = bytes / 1024 / 1024 / 1024
  } else if (bytes > 512 * 1024) { // >= 0.5MB
    unit = 'megabyte'
    n = bytes / 1024 / 1024
  } else if (bytes > 512) { // >= 0.5kB
    unit = 'kilobyte'
    n = bytes / 1024
  } else {
    unit = 'byte'
    n = bytes
  }

  return new Intl.NumberFormat('en-US', { style: 'unit', unit }).format(n.toFixed(n >= 5 ? 0 : 1))
}

function DownloadLink (props) {
  const { format, href, bytes } = props

  return (
    <span className='download'>
      <a
        download
        href={href}
      >
        <tt className='format'>.{format}</tt>
      </a>
      <span className='size'>{formatNBytes(bytes)}</span>
    </span>
  )
}
DownloadLink.propTypes = {
  format: PropTypes.oneOf(['parquet', 'csv', 'json']).isRequired,
  href: PropTypes.string.isRequired,
  bytes: PropTypes.number.isRequired
}

export default function DownloadList (props) {
  const { datapackage } = props
  const tables = gatherTables(datapackage.resources)

  return (
    <ul>
      {tables.map(({ name, title, paths }) => (
        <li key={name}>
          <h4>{title}</h4>
          <p>
            <tt className='name'>{name}</tt>
            {['parquet', 'csv', 'json'].map(format => (
              <DownloadLink
                key={format}
                format={format}
                href={paths[format].href}
                bytes={paths[format].bytes}
              />
            ))}
          </p>
        </li>
      ))}
    </ul>
  )
}
DownloadList.propTypes = {
  datapackage: PropTypes.shape({
    resources: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      format: PropTypes.oneOf(['parquet', 'csv', 'json']),
      bytes: PropTypes.number.isRequired
    }).isRequired).isRequired
  })
}
