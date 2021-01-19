import React from 'react'
import PropTypes from 'prop-types'
import Markdown from 'react-markdown'
import BlockFrame from './BlockFrame'
import MarkdownEditor from './MarkdownEditor'

export default function TextBlock (props) {
  const {
    block,
    isReadOnly,
    onClickDelete,
    onClickMoveUp = null,
    onClickMoveDown = null,
    setBlockMarkdown
  } = props
  const { slug, markdown } = block
  const [editedMarkdown, setEditedMarkdown] = React.useState(null) // non-null means, "editing"
  const handleClickEdit = React.useMemo(() => {
    if (editedMarkdown !== null) return null // so the button is disabled
    return () => setEditedMarkdown(markdown)
  }, [editedMarkdown, setEditedMarkdown])

  const handleChange = setEditedMarkdown
  const handleCancel = React.useCallback(() => setEditedMarkdown(null), [setEditedMarkdown])
  const handleSubmit = React.useCallback(() => {
    if (editedMarkdown === '') {
      onClickDelete(slug)
    } else {
      setBlockMarkdown(slug, editedMarkdown)
    }
    setEditedMarkdown(null) // stop editing
  }, [slug, editedMarkdown, setBlockMarkdown])

  return (
    <BlockFrame
      className='block-text'
      slug={block.slug}
      isReadOnly={isReadOnly}
      onClickDelete={onClickDelete}
      onClickMoveUp={onClickMoveUp}
      onClickMoveDown={onClickMoveDown}
      onClickEdit={handleClickEdit}
    >
      {editedMarkdown === null ? (
        <div className='markdown'>
          <Markdown source={markdown} />
        </div>
      ) : (
        <MarkdownEditor
          value={editedMarkdown}
          onChange={handleChange}
          onCancel={handleCancel}
          onSubmit={handleSubmit}
        />
      )}
    </BlockFrame>
  )
}
TextBlock.propTypes = {
  block: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    markdown: PropTypes.string.isRequired
  }).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func, // or null, if this is the top block
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
