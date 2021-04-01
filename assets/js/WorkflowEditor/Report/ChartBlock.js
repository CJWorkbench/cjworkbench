import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../../propTypes'
import BlockFrame from './BlockFrame'
import { useChartIframeSrcWithDataUrlSubscription } from '../../ChartIframe'

export default function ChartBlock ({
  workflowIdOrSecretId,
  block,
  isReadOnly,
  onClickDelete,
  onClickMoveDown,
  onClickMoveUp
}) {
  const { slug, step } = block
  const [iframeEl, setIframeEl] = React.useState(null)
  const src = useChartIframeSrcWithDataUrlSubscription({
    workflowIdOrSecretId,
    moduleSlug: step.module,
    stepSlug: step.slug,
    deltaId: step.cached_render_result_delta_id,
    iframeEl
  })

  return (
    <BlockFrame
      className='block-chart'
      slug={slug}
      isReadOnly={isReadOnly}
      onClickDelete={onClickDelete}
      onClickMoveDown={onClickMoveDown}
      onClickMoveUp={onClickMoveUp}
    >
      <iframe src={src === null ? 'about:blank' : src} ref={setIframeEl} />
    </BlockFrame>
  )
}
ChartBlock.propTypes = {
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  block: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    step: PropTypes.shape({
      slug: PropTypes.string.isRequired,
      cached_render_result_delta_id: PropTypes.number.isRequired,
      module: PropTypes.string.isRequired
    }).isRequired
  }).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func // or null, if this is the top block
}
