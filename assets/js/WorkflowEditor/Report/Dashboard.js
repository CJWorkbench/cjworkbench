import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../../propTypes'
import Report from './Report'
import ShareCard from './ShareCard'

export default function Dashboard ({
  workflowIdOrSecretId,
  workflow,
  blocks,
  reportableTabs,
  addBlock,
  deleteBlock,
  reorderBlocks,
  isReadOnly,
  setBlockMarkdown
}) {
  return (
    <article className='report'>
      <ShareCard
        workflowId={workflow.id}
        secretId={workflow.secret_id}
        isPublic={workflow.public}
      />
      <Report
        workflowIdOrSecretId={workflowIdOrSecretId}
        workflow={workflow}
        isReadOnly={isReadOnly}
        blocks={blocks}
        reportableTabs={reportableTabs}
        addBlock={addBlock}
        deleteBlock={deleteBlock}
        reorderBlocks={reorderBlocks}
        setBlockMarkdown={setBlockMarkdown}
      />
    </article>
  )
}
Dashboard.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    public: PropTypes.bool.isRequired,
    secret_id: PropTypes.string.isRequired // "" for no secret
  }).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  blocks: PropTypes.array.isRequired,
  reportableTabs: PropTypes.array.isRequired,
  addBlock: PropTypes.func.isRequired, // func(position, { type, ... }) => undefined
  deleteBlock: PropTypes.func.isRequired, // func(slug) => undefined
  reorderBlocks: PropTypes.func.isRequired, // func([slugs]) => undefined
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
