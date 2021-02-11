import { PureComponent } from 'react'

// https://reactjs.org/docs/higher-order-components.html
export function withFetchedData (
  WrappedComponent,
  dataName,
  fetchData,
  fetchDataCacheId
) {
  return class extends PureComponent {
    state = {
      data: null,
      loading: false
    }

    _reload () {
      const cacheId = fetchDataCacheId(this.props)

      // Keep state.data unchanged, until we solve
      // https://www.pivotaltracker.com/story/show/158034731. After that, we
      // should probably change this to setState({data: null})
      this.setState({ loading: true })

      fetchData(this.props).then(data => {
        if (this.unmounted) return
        if (fetchDataCacheId(this.props) !== cacheId) return // ignore wrong response in race

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
      if (fetchDataCacheId(this.props) !== fetchDataCacheId(prevProps)) {
        this._reload()
      }
    }

    render () {
      const { loading, data } = this.state

      const props = {
        [dataName]: data,
        loading: loading,
        ...this.props
      }

      return <WrappedComponent {...props} />
    }
  }
}
