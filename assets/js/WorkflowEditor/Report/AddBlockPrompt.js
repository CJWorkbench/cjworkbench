import React from 'react'
import PropTypes from 'prop-types'
import AddTextBlockPrompt from './AddTextBlockPrompt'
import AddTableBlockPrompt from './AddTableBlockPrompt'
import AddChartBlockPrompt from './AddChartBlockPrompt'
import MarkdownEditor from './MarkdownEditor'

export default function AddBlockPrompt ({ position, tabs, onSubmit }) {
  const [openMenu, setOpenMenu] = React.useState(null) // null, 'table', 'chart'
  const [markdown, setMarkdown] = React.useState('')
  const [isEditingMarkdown, setEditingMarkdown] = React.useState(false)
  const handleClickAddText = React.useCallback(() => {
    setEditingMarkdown(!isEditingMarkdown)
  }, [isEditingMarkdown, setEditingMarkdown])
  const handleOpenChartMenu = React.useCallback(() => {
    setOpenMenu('chart')
    setEditingMarkdown(false)
  }, [setOpenMenu])
  const handleOpenTableMenu = React.useCallback(() => {
    setOpenMenu('table')
    setEditingMarkdown(false)
  }, [setOpenMenu])
  const handleCloseMenu = React.useCallback(() => {
    setOpenMenu(null)
  }, [setOpenMenu])

  const handleCancelAddText = React.useCallback(() => {
    setMarkdown('')
    setEditingMarkdown(false)
  }, [setMarkdown, setEditingMarkdown])
  const handleSubmitText = React.useCallback(() => {
    if (markdown) {
      onSubmit(position, { type: 'text', markdown })
      setMarkdown('')
    }
    setEditingMarkdown(false)
  }, [position, markdown, setMarkdown, setEditingMarkdown, onSubmit])
  const handleSubmitTable = React.useCallback(block => {
    onSubmit(position, { type: 'table', ...block })
  }, [position, onSubmit])
  const handleSubmitChart = React.useCallback(block => {
    onSubmit(position, { type: 'chart', ...block })
  }, [position, onSubmit])
  return (
    <div className={`add-block-prompt${(openMenu || isEditingMarkdown) ? ' active' : ''}`}>
      <div className='actions'>
        <AddTextBlockPrompt active={isEditingMarkdown} onClick={handleClickAddText} />
        <AddTableBlockPrompt
          tabs={tabs}
          isMenuOpen={openMenu === 'table'}
          onOpenMenu={handleOpenTableMenu}
          onCloseMenu={handleCloseMenu}
          onSubmit={handleSubmitTable}
        />
        <AddChartBlockPrompt
          tabs={tabs}
          isMenuOpen={openMenu === 'chart'}
          onOpenMenu={handleOpenChartMenu}
          onCloseMenu={handleCloseMenu}
          onSubmit={handleSubmitChart}
        />
      </div>
      {isEditingMarkdown ? (
        <MarkdownEditor
          value={markdown}
          onChange={setMarkdown}
          onCancel={handleCancelAddText}
          onSubmit={handleSubmitText}
        />
      ) : null}
    </div>
  )
}
AddBlockPrompt.propTypes = {
  position: PropTypes.number.isRequired,
  tabs: PropTypes.arrayOf(PropTypes.shape({
    slug: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    chartSteps: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      moduleName: PropTypes.string.isRequired
    }).isRequired).isRequired
  }).isRequired).isRequired,
  onSubmit: PropTypes.func.isRequired // func(position, { type, ... }) => undefined
}
