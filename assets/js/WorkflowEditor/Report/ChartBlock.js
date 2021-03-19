import PropTypes from 'prop-types'
import BlockFrame from './BlockFrame'

export default function ChartBlock ({
  workflowId,
  block,
  isReadOnly,
  onClickDelete,
  onClickMoveDown,
  onClickMoveUp
}) {
  const { slug, step } = block
  const dataUrl = `/workflows/${workflowId}/steps/${step.slug}/delta-${step.cached_render_result_delta_id}/result-json.json`
  const src = `/api/wfmodules/${step.id}/output?dataUrl=${encodeURIComponent(dataUrl)}`

  return (
    <BlockFrame
      className='block-chart'
      slug={slug}
      isReadOnly={isReadOnly}
      onClickDelete={onClickDelete}
      onClickMoveDown={onClickMoveDown}
      onClickMoveUp={onClickMoveUp}
    >
      {step.cached_render_result_delta_id ? <iframe src={src} /> : null}
    </BlockFrame>
  )
}
ChartBlock.propTypes = {
  workflowId: PropTypes.number.isRequired,
  block: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    step: PropTypes.shape({
      id: PropTypes.number.isRequired, // TODO make API use workflowId + stepSlug
      cached_render_result_delta_id: PropTypes.number // null if never rendered
    }).isRequired
  }).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func // or null, if this is the top block
}
