import React from 'react'

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
        <div className="caught-error">
          We ran into an unexpected error. Please refresh the page to retry.
        </div>
      )
    } else {
      return this.props.children
    }
  }
}
