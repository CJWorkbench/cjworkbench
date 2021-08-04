import React from 'react'
import PropTypes from 'prop-types'

export default function CodePandas (props) {
  const { datapackage } = props
  const { resources } = datapackage
  const parquetResources = resources.filter(r => r.format === 'parquet')

  const url = datapackage.path.replace(/\/r\d+/, '')

  return (
    <>
      <h2>Example code with Python and Pandas</h2>
      <h3>One-time installation</h3>
      <p>Once per computer, you'll need to install Pandas and a Parquet reader:</p>
      <pre className='lang-bash'>
        python3 -mpip install "pandas&gt;=1.3.0" "pyarrow&gt;=5.0.0"
      </pre>

      <h3>Load data in Python</h3>
      <pre className='lang-python'>
        {[
          'import json',
          'from urllib.request import urlopen',
          '',
          'import pandas',
          '',
          `datapackage_url = "${url}"`,
          '',
          'with urlopen(datapackage_url) as f:',
          '    datapackage = json.load(f)',
          '',
          'resources = [r for r in datapackage["resources"] if r["format"] == "parquet"]',
          'tables = {',
          '  resource["name"]: pandas.read_parquet(resource["path"], use_nullable_dtypes=True)',
          '  for resource in resources',
          '}',
          '',
          ...parquetResources.map(({ name, title }) => `print(tables["${name}"])  # ${title}`)
        ].join('\n')}
      </pre>
    </>
  )
}
CodePandas.propTypes = {
  datapackage: PropTypes.shape({
    path: PropTypes.string.isRequired,
    resources: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      format: PropTypes.oneOf(['csv', 'json', 'parquet']).isRequired
    }).isRequired).isRequired
  })
}
