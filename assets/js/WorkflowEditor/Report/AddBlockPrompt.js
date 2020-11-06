import React from 'react'
import PropTypes from 'prop-types'
import AddTextBlockPrompt from './AddTextBlockPrompt'
import AddTableBlockPrompt from './AddTableBlockPrompt'
import AddChartBlockPrompt from './AddChartBlockPrompt'

export default function AddBlockPrompt ({ position, tabs, onSubmit }) {
  const handleSubmitText = React.useCallback(block => {
    onSubmit(position, { type: 'text', ...block })
  }, [position, onSubmit])
  const handleSubmitTable = React.useCallback(block => {
    onSubmit(position, { type: 'table', ...block })
  }, [position, onSubmit])
  const handleSubmitChart = React.useCallback(block => {
    onSubmit(position, { type: 'chart', ...block })
  }, [position, onSubmit])
  return (
    <div className='add-block-prompt'>
      <AddTextBlockPrompt onSubmit={handleSubmitText} />
      <AddTableBlockPrompt tabs={tabs} onSubmit={handleSubmitTable} />
      <AddChartBlockPrompt tabs={tabs} onSubmit={handleSubmitChart} />
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
