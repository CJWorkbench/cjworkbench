import React from 'react'
import PropTypes from 'prop-types'

// https://reactjs.org/docs/higher-order-components.html
export function withFetchedData (WrappedComponent, dataName) {
  return class extends React.PureComponent {
    static propTypes = {
      fetchData: PropTypes.func.isRequired, // fn() => Promise[data]
      fetchDataCacheId: PropTypes.string.isRequired, // unique string: when it changes, call fetchData()
    }

    state = {
      data: null,
      loading: false
    }

    _reload () {
      const fetchDataCacheId = this.props.fetchDataCacheId

      // Keep state.data unchanged, until we solve
      // https://www.pivotaltracker.com/story/show/158034731. After that, we
      // should probably change this to setState({data: null})
      this.setState({ loading: true })

      this.props.fetchData()
        .then(data => {
          if (this.unmounted) return
          if (this.props.fetchDataCacheId !== fetchDataCacheId) return // ignore wrong response in race

          this.setState({
            loading: false,
            data
          })
        })
    }

    componentDidMount () {
      this._reload()
    }

    componentWillUnmount () {
      this.unmounted = true
    }

    componentDidUpdate (prevProps) {
      if (prevProps.fetchDataCacheId !== this.props.fetchDataCacheId) {
        this._reload()
      }
    }

    render () {
      const props = Object.assign({
        [dataName]: this.state.data,
        loading: this.state.loading
      }, this.props)
      delete props.fetchData
      delete props.fetchDataCacheId

      return <WrappedComponent {...props} />
    }
  }
}
