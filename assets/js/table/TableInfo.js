import React from 'react'
import PropTypes from 'prop-types'
import propTypes from '../propTypes'
import ExportModal from '../ExportModal'
import SelectedRowsActions from './SelectedRowsActions'
import { Trans } from '@lingui/macro'

const numberFormat = new Intl.NumberFormat('en-US')

export default class TableInfo extends React.PureComponent {
  static propTypes = {
    nRows: PropTypes.number, // or null if unknown
    nColumns: PropTypes.number, // or null if unknown
    isReadOnly: PropTypes.bool.isRequired,
    workflowId: propTypes.workflowId.isRequired,
    stepId: PropTypes.number, // or null if none selected
    stepSlug: PropTypes.string, // or null if none selected
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired).isRequired
  }

  state = {
    isExportModalOpen: false
  }

  handleClickExport = () => {
    this.setState({ isExportModalOpen: true })
  }

  closeExportModal = ev => {
    this.setState({ isExportModalOpen: false })
  }

  render () {
    const {
      nRows,
      nColumns,
      workflowId,
      stepSlug,
      stepId,
      selectedRowIndexes,
      isReadOnly
    } = this.props
    const { isExportModalOpen } = this.state

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
                selectedRowIndexes={selectedRowIndexes}
                stepId={stepId}
              />
              )}
        </div>

        {!stepSlug
          ? null
          : (
            <>
              <button className='export-table' onClick={this.handleClickExport}>
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
                workflowId={workflowId}
                stepSlug={stepSlug}
                toggle={this.closeExportModal}
              />
            </>
            )}
      </div>
    )
  }
}
