import React from 'react'
import PropTypes from 'prop-types'

export default function CodePandas (props) {
  const { datapackage } = props
  const { resources } = datapackage
  const parquetResources = resources
    .filter(r => r.format === 'parquet')
    .map(({ name, path }) => ({
      name: name.substring(0, name.indexOf('_')),
      path
    }))

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
          'import pandas',
          '',
          'tables = {',
          '  name: pandas.read_parquet(path, use_nullable_dtypes=True)',
          '  for name, path in [',
          ...parquetResources.map(({ name, path }) => `    ("${name}", "${path}"),`),
          '  ]',
          '}',
          '',
          `print(tables["${parquetResources[0].name}"])`
        ].join('\n')}
      </pre>
    </>
  )
}
CodePandas.propTypes = {
  datapackage: PropTypes.shape({
    resources: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      path: PropTypes.string.isRequired,
      format: PropTypes.oneOf(['csv', 'json', 'parquet']).isRequired
    }).isRequired).isRequired
  })
}
