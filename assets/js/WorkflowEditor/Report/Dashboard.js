import PropTypes from 'prop-types'
import Report from './Report'
import ShareCard from './ShareCard'

export default function Dashboard ({ workflow, blocks, reportableTabs, addBlock, deleteBlock, reorderBlocks, setBlockMarkdown }) {
  return (
    <article className='report'>
      <ShareCard workflowId={workflow.id} isPublic={workflow.public} />
      <Report
        workflow={workflow}
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
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    public: PropTypes.bool.isRequired
  }).isRequired,
  blocks: PropTypes.array.isRequired,
  reportableTabs: PropTypes.array.isRequired,
  addBlock: PropTypes.func.isRequired, // func(position, { type, ... }) => undefined
  deleteBlock: PropTypes.func.isRequired, // func(slug) => undefined
  reorderBlocks: PropTypes.func.isRequired, // func([slugs]) => undefined
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
