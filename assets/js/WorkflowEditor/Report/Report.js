import { useCallback, Fragment } from 'react'
import PropTypes from 'prop-types'
import ReportHeader from './ReportHeader'
import Block from './Block'
import AddBlockPrompt from './AddBlockPrompt'
import propTypes from '../../propTypes'

export default function Report ({
  workflow,
  workflowIdOrSecretId,
  blocks,
  reportableTabs,
  addBlock,
  deleteBlock,
  reorderBlocks,
  setBlockMarkdown,
  isReadOnly
}) {
  const handleClickDelete = deleteBlock
  const handleClickMoveUp = useCallback(
    slug => {
      const slugs = blocks.map(b => b.slug) // we're going to mutate it
      const index = slugs.indexOf(slug)
      if (index > 0) {
        slugs.splice(index - 1, 2, slug, slugs[index - 1])
        reorderBlocks(slugs)
      }
    },
    [blocks, reorderBlocks]
  )
  const handleClickMoveDown = useCallback(
    slug => {
      const slugs = blocks.map(b => b.slug) // we're going to mutate it
      const index = slugs.indexOf(slug)
      if (index >= 0 && index < slugs.length - 1) {
        slugs.splice(index, 2, slugs[index + 1], slug)
        reorderBlocks(slugs)
      }
    },
    [blocks, reorderBlocks]
  )

  return (
    <div
      className={`report-container ${
        isReadOnly ? 'report-read-only' : 'report-read-write'
      }`}
    >
      {isReadOnly
        ? null
        : (
          <AddBlockPrompt
            position={0}
            tabs={reportableTabs}
            onSubmit={addBlock}
          />
          )}
      {blocks.map((block, position) => (
        <Fragment key={block.slug}>
          <Block
            workflowIdOrSecretId={workflowIdOrSecretId}
            block={block}
            isReadOnly={isReadOnly}
            onClickDelete={handleClickDelete}
            onClickMoveUp={position === 0 ? null : handleClickMoveUp}
            onClickMoveDown={
              position === blocks.length - 1 ? null : handleClickMoveDown
            }
            setBlockMarkdown={setBlockMarkdown}
          />
          {isReadOnly
            ? null
            : (
              <AddBlockPrompt
                position={position + 1}
                tabs={reportableTabs}
                onSubmit={addBlock}
              />
              )}
        </Fragment>
      ))}
    </div>
  )
}
Report.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  workflow: PropTypes.shape({
    name: PropTypes.string.isRequired
  }).isRequired,
  blocks: PropTypes.array.isRequired,
  reportableTabs: PropTypes.array.isRequired,
  addBlock: PropTypes.func.isRequired, // func(position, { type, ... }) => undefined
  deleteBlock: PropTypes.func.isRequired, // func(slug) => undefined
  reorderBlocks: PropTypes.func.isRequired, // func([slugs]) => undefined
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
