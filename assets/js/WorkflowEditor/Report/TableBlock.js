import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'
import BlockFrame from './BlockFrame'
import Table from '../../Report/Table'

export default function TableBlock ({ block, isReadOnly, onClickDelete, onClickMoveDown, onClickMoveUp }) {
  const { slug, tab } = block
  const { name, outputStep } = tab

  return (
    <BlockFrame
      className='block-table'
      slug={slug}
      isReadOnly={isReadOnly}
      onClickDelete={onClickDelete}
      onClickMoveDown={onClickMoveDown}
      onClickMoveUp={onClickMoveUp}
    >
      <h2>{name}</h2>
      {outputStep && outputStep.outputStatus === 'ok' ? ([
        <Table key='table' stepSlug={outputStep.slug} />,
        <a key='download' download href={`/public/moduledata/live/${outputStep.id}.csv`}>
          <Trans id='js.WorkflowEditor.Report.TableBlock.downloadCsv'>Download spreadsheet</Trans>
        </a>
      ]) : (
        <p className='no-table-data'>
          <Trans id='js.WorkflowEditor.Report.TableBlock.noTableData'>No table data</Trans>
        </p>
      )}
    </BlockFrame>
  )
}
TableBlock.propTypes = {
  block: PropTypes.shape({
    slug: PropTypes.string.isRequired,
    tab: PropTypes.shape({
      name: PropTypes.string.isRequired,
      outputStep: PropTypes.shape({
        id: PropTypes.number.isRequired,
        slug: PropTypes.string.isRequired,
        outputStatus: PropTypes.oneOf(['ok', 'unreachable', 'error']), // or null for rendering
        deltaId: PropTypes.number.isRequired
      }) // null if the tab has no [cached] output
    }).isRequired
  }).isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func // or null, if this is the top block
}
