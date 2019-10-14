import React from 'react'
import { Trans } from '@lingui/macro'

export default class ErrorBoundary extends React.PureComponent {
  state = {
    error: null
  }

  static getDerivedStateFromError (error) {
    return { error }
  }

  componentDidCatch (error, info) {
    console.log('Error caught in ErrorBoundary', error, info)
  }

  render () {
    if (this.state.error) {
      return (
        <div className='caught-error'>
          <Trans id='workflow.workbenchsomethingwrong'>Something is wrong.</Trans> <br /> <Trans id='workflow.workbenchrefresh'> Please refresh the page.</Trans> 
        </div>
      )
    } else {
      return this.props.children
    }
  }
}
