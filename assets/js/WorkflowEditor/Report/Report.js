import React from 'react'
import PropTypes from 'prop-types'
import ReportHeader from './ReportHeader'
import Block from './Block'
import AddBlockPrompt from './AddBlockPrompt'

export default function Report ({
  workflow, blocks, reportableTabs, addBlock, deleteBlock, reorderBlocks, setBlockMarkdown
}) {
  const handleClickDelete = deleteBlock
  const handleClickMoveUp = React.useCallback(slug => {
    const slugs = blocks.map(b => b.slug) // we're going to mutate it
    const index = slugs.indexOf(slug)
    if (index > 0) {
      slugs.splice(index - 1, 2, slug, slugs[index - 1])
      reorderBlocks(slugs)
    }
  }, [blocks, reorderBlocks])
  const handleClickMoveDown = React.useCallback(slug => {
    const slugs = blocks.map(b => b.slug) // we're going to mutate it
    const index = slugs.indexOf(slug)
    if (index >= 0 && index < slugs.length - 1) {
      slugs.splice(index, 2, slugs[index + 1], slug)
      reorderBlocks(slugs)
    }
  }, [blocks, reorderBlocks])

  return (
    <div className='report-container'>
      <ReportHeader title={workflow.name} />
      {blocks.map((block, position) => (
        <React.Fragment key={block.slug}>
          <AddBlockPrompt position={position} tabs={reportableTabs} onSubmit={addBlock} />
          <Block
            block={block}
            onClickDelete={handleClickDelete}
            onClickMoveUp={position === 0 ? null : handleClickMoveUp}
            onClickMoveDown={position === blocks.length - 1 ? null : handleClickMoveDown}
            setBlockMarkdown={setBlockMarkdown}
          />
        </React.Fragment>
      ))}
      <AddBlockPrompt position={blocks.length} tabs={reportableTabs} onSubmit={addBlock} />
    </div>
  )
}
Report.propTypes = {
  workflow: PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired
  }).isRequired,
  blocks: PropTypes.array.isRequired,
  reportableTabs: PropTypes.array.isRequired,
  addBlock: PropTypes.func.isRequired, // func(position, { type, ... }) => undefined
  deleteBlock: PropTypes.func.isRequired, // func(slug) => undefined
  reorderBlocks: PropTypes.func.isRequired, // func([slugs]) => undefined
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
