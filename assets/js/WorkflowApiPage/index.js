import React from 'react'
import PropTypes from 'prop-types'
import CodePandas from './CodePandas'
import DownloadList from './DownloadList'
import ShareUrl from '../components/ShareUrl'

function ExternalLink (props) {
  const { children, href } = props
  return (
    <a href={href} target='_blank' rel='noopener noreferrer'>
      {children}
    </a>
  )
}
ExternalLink.propTypes = {
  href: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired
}

export default function WorkflowApiPage (props) {
  const { workflow } = props

  return (
    <article>
      <header>
        <h1>{workflow.name} API</h1>
        <p className='subheading'>Access these tables with any toolkit</p>
      </header>
      <section className='files'>
        <h2>Download files</h2>
        <DownloadList datapackage={workflow.dataset} />
        <h3>Do I want CSV, JSON or Parquet?</h3>
        <ul>
          <li><strong>Parquet</strong> if your tools can read it -- tools like <ExternalLink href='https://pandas.pydata.org/'>Pandas</ExternalLink>, <ExternalLink href='https://www.r-project.org/'>R</ExternalLink> and <ExternalLink href='https://spark.apache.org/'>Spark</ExternalLink>.</li>
          <li><strong>JSON</strong> for web-browser JavaScript, when JSON size is under 1MB.</li>
          <li><strong>CSV</strong> otherwise.</li>
        </ul>
        <p>See <ExternalLink href='https://github.com/CJWorkbench/cjworkbench/wiki/Exported-tables-and-their-columns'>file-format documentation</ExternalLink>.</p>
      </section>
      <section className='datapackages'>
        <h2>Frictionless Data Package URLs</h2>
        <p>To download all tables and column information, use one of these URLs with a tool like <ExternalLink href='https://github.com/datopian/data-cli'>data-cli</ExternalLink>:</p>
        <ShareUrl url={workflow.dataset.path.replace(/\/r\d+/, '')} download={false} go={false} />
      </section>
      <section className='code'>
        <CodePandas datapackage={workflow.dataset} />
      </section>
    </article>
  )
}
WorkflowApiPage.propTypes = {
  workflow: PropTypes.shape({
    dataset: PropTypes.object // or null
  }).isRequired
}
