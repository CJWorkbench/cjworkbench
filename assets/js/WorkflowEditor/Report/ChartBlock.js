import React from 'react'
import PropTypes from 'prop-types'
import BlockFrame from './BlockFrame'

export default function ChartBlock ({ block, onClickDelete, onClickMoveDown, onClickMoveUp }) {
  const { slug, step } = block
  const deltaId = step.cached_render_result_delta_id || 'rendering'

  return (
    <BlockFrame
      className='block-chart'
      slug={slug}
      onClickDelete={onClickDelete}
      onClickMoveDown={onClickMoveDown}
      onClickMoveUp={onClickMoveUp}
    >
      <iframe src={`/api/wfmodules/${step.id}/output#revision=${deltaId}`} />
    </BlockFrame>
  )
}
ChartBlock.propTypes = {
  block: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    step: PropTypes.shape({
      id: PropTypes.number.isRequired, // TODO make API use workflowId + stepSlug
      cached_render_result_delta_id: PropTypes.number // null if never rendered
    }).isRequired
  }).isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func // or null, if this is the top block
}
