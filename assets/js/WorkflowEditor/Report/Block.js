import PropTypes from 'prop-types'
import propTypes from '../../propTypes'
import ChartBlock from './ChartBlock'
import TableBlock from './TableBlock'
import TextBlock from './TextBlock'

const Components = {
  chart: ChartBlock,
  table: TableBlock,
  text: TextBlock
}

/**
 * Choose among ChartBlock, TableBlock and TextBlock, depending on `block.type`
 * */
export default function Block (props) {
  const {
    workflowIdOrSecretId,
    block,
    isReadOnly,
    onClickDelete,
    onClickMoveUp = null,
    onClickMoveDown = null,
    setBlockMarkdown
  } = props
  const Component = Components[block.type]
  return (
    <Component
      workflowIdOrSecretId={workflowIdOrSecretId}
      block={block}
      isReadOnly={isReadOnly}
      onClickDelete={onClickDelete}
      onClickMoveUp={onClickMoveUp}
      onClickMoveDown={onClickMoveDown}
      setBlockMarkdown={setBlockMarkdown}
    />
  )
}
Block.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  block: PropTypes.oneOfType([
    PropTypes.exact({
      slug: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text']).isRequired,
      markdown: PropTypes.string.isRequired
    }).isRequired,
    PropTypes.exact({
      slug: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['chart']).isRequired,
      step: PropTypes.object.isRequired
    }).isRequired,
    PropTypes.exact({
      slug: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['table']).isRequired,
      tab: PropTypes.object.isRequired
    }).isRequired
  ]).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func, // or null, if this is the top block
  setBlockMarkdown: PropTypes.func.isRequired // func(slug, markdown) => undefined
}
