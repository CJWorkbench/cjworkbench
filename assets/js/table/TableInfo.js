import React from 'react'
import PropTypes from 'prop-types'
import ExportModal from '../ExportModal'

const numberFormat = new Intl.NumberFormat('en-US')

export default class TableInfo extends React.PureComponent {
  static propTypes = {
    nRows: PropTypes.number, // or null if unknown
    nColumns: PropTypes.number, // or null if unknown
    selectedWfModuleId: PropTypes.number, // or null if none selected
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired).isRequired
  }

  state = {
    isExportModalOpen: false
  }

  openExportModal = () => {
    this.setState({ isExportModalOpen: true })
  }

  closeExportModal = () => {
    this.setState({ isExportModalOpen: false })
  }

  render () {
    const { nRows, nColumns, selectedWfModuleId } = this.props
    const { isExportModalOpen } = this.state

    const nRowsString = nRows === null ? '' : numberFormat.format(nRows)
    const nColumnsString = nColumns === null ? '' : numberFormat.format(nColumns)

    return (
      <div className="outputpane-header">
        <div className="table-info-container">
          <div className='table-info'>
            <div className='data'>Rows</div>
            <div className='value'>{nRowsString}</div>
          </div>
          <div className='table-info'>
            <div className='data'>Columns</div>
            <div className='value'>{nColumnsString}</div>
          </div>
        </div>
              
        {!selectedWfModuleId ? null : (
          <div className="export-table" onClick={this.openExportModal}>
            <i className="icon-download" />
            <span>CSV</span>
            <span className="feed">JSON FEED</span>
            <ExportModal
              open={isExportModalOpen}
              wfModuleId={selectedWfModuleId}
              onClose={this.closeExportModal}
            />
          </div>
        )}
      </div>
    )
  }
}
