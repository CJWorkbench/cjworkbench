import React from 'react'
import PropTypes from 'prop-types'
import * as propTypes from './propTypes'
import Tab from './Tab'

function EmptyReport () {
  return (
    <article className='report'>
      <p className='empty-report'>
        There are no charts in this Workflow. Add charts to tabs, and they'll appear here.
      </p>
    </article>
  )
}


const Report = React.memo(function Report ({ workflowId }) {
  const [ height, setHeight ] = React.useState(0)
  const iframeRef = React.useRef(null)
  const watchHeight = React.useCallback(() => {
    const iframe = iframeRef.current
    if (!iframe) return undefined

    function update () {
      const doc = iframe.contentDocument
      if (!doc) return
      const root = doc.documentElement
      if (!root) return
      const rect = root.getBoundingClientRect()
      if (!rect) return
      setHeight(Math.ceil(rect.height))
    }

    iframe.contentWindow.addEventListener('load', update)
    iframe.contentWindow.addEventListener('resize', update)
    update()

    // No need to register destructors: if the iframe goes away, its event
    // listeners will go away, too.
  }, [ iframeRef.current ])

  return (
    <article className='report'>
      <div className='iframe-container'>
        <iframe
          ref={iframeRef}
          src={`/workflows/${workflowId}/report`}
          height={height}
          onLoad={watchHeight}
        />
      </div>
    </article>
  )
})
Report.propTypes = {
  workflowId: PropTypes.number.isRequired
}
export default Report
