import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import ExportModal from '../ExportModal'
import SelectedRowsActions from './SelectedRowsActions'
import { Trans } from '@lingui/macro'

const numberFormat = new Intl.NumberFormat('en-US')

export default function TableInfo (props) {
  const [isExportModalOpen, setExportModalOpen] = React.useState(false)

  const handleClickExport = React.useCallback(
    () => setExportModalOpen(true),
    [setExportModalOpen]
  )

  const handleCloseExportModal = React.useCallback(
    () => setExportModalOpen(false),
    [setExportModalOpen]
  )

  const {
    nRows,
    nColumns,
    workflowIdOrSecretId,
    stepSlug,
    stepId,
    rowSelection,
    isReadOnly
  } = props

  const nRowsString = nRows === null
    ? ''
    : numberFormat.format(nRows)
  const nColumnsString = nColumns === null
    ? ''
    : numberFormat.format(nColumns)

  return (
    <div className='outputpane-header'>
      <div className='table-info-container'>
        <div className='table-info'>
          <div className='data'>
            <Trans
              id='js.table.TableInfo.rows'
              comment='This should be all-caps for styling reasons'
            >
              ROWS
            </Trans>
          </div>
          <div className='value'>{nRowsString}</div>
        </div>
        <div className='table-info'>
          <div className='data'>
            <Trans
              id='js.table.TableInfo.columns'
              comment='This should be all-caps for styling reasons'
            >
              COLUMNS
            </Trans>
          </div>
          <div className='value'>{nColumnsString}</div>
        </div>
        {isReadOnly
          ? null
          : (
            <SelectedRowsActions
              rowSelection={rowSelection}
              stepId={stepId}
            />
            )}
      </div>

      {!stepSlug
        ? null
        : (
          <>
            <button className='export-table' onClick={handleClickExport}>
              <i className='icon-download' />
              <Trans
                id='js.table.TableInfo.export'
                comment='This should be all-caps for styling reasons'
              >
                EXPORT
              </Trans>
            </button>
            <ExportModal
              open={isExportModalOpen}
              workflowIdOrSecretId={workflowIdOrSecretId}
              stepSlug={stepSlug}
              toggle={handleCloseExportModal}
            />
          </>
          )}
    </div>
  )
}
TableInfo.propTypes = {
  nRows: PropTypes.number, // or null if unknown
  nColumns: PropTypes.number, // or null if unknown
  isReadOnly: PropTypes.bool.isRequired,
  workflowIdOrSecretId: propTypes.workflowId.isRequired,
  stepId: PropTypes.number, // or null if none selected
  stepSlug: PropTypes.string, // or null if none selected
  rowSelection: PropTypes.instanceOf(Uint8Array).isRequired
}
