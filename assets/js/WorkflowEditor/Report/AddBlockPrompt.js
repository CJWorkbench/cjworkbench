import { useState, useCallback } from 'react'
import PropTypes from 'prop-types'
import AddTextBlockPrompt from './AddTextBlockPrompt'
import AddTableBlockPrompt from './AddTableBlockPrompt'
import AddChartBlockPrompt from './AddChartBlockPrompt'
import MarkdownEditor from './MarkdownEditor'

export default function AddBlockPrompt ({ position, tabs, onSubmit }) {
  const [openMenu, setOpenMenu] = useState(null) // null, 'table', 'chart'
  const [markdown, setMarkdown] = useState('')
  const [isEditingMarkdown, setEditingMarkdown] = useState(false)
  const handleClickAddText = useCallback(() => {
    setEditingMarkdown(!isEditingMarkdown)
  }, [isEditingMarkdown, setEditingMarkdown])
  const handleOpenChartMenu = useCallback(() => {
    setOpenMenu('chart')
    setEditingMarkdown(false)
  }, [setOpenMenu])
  const handleOpenTableMenu = useCallback(() => {
    setOpenMenu('table')
    setEditingMarkdown(false)
  }, [setOpenMenu])
  const handleCloseMenu = useCallback(() => {
    setOpenMenu(null)
  }, [setOpenMenu])

  const handleCancelAddText = useCallback(() => {
    setMarkdown('')
    setEditingMarkdown(false)
  }, [setMarkdown, setEditingMarkdown])
  const handleSubmitText = useCallback(() => {
    if (markdown) {
      onSubmit(position, { type: 'text', markdown })
      setMarkdown('')
    }
    setEditingMarkdown(false)
  }, [position, markdown, setMarkdown, setEditingMarkdown, onSubmit])
  const handleSubmitTable = useCallback(block => {
    onSubmit(position, { type: 'table', ...block })
  }, [position, onSubmit])
  const handleSubmitChart = useCallback(block => {
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
