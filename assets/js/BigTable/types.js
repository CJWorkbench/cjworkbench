import PropTypes from 'prop-types'

const columnDefinitionType = PropTypes.shape({
  width: PropTypes.number.isRequired,
  headerComponent: PropTypes.elementType.isRequired,
  valueComponent: PropTypes.elementType.isRequired
})

const loadedTileType = PropTypes.arrayOf(PropTypes.array.isRequired).isRequired
const errorTileType = PropTypes.shape({
  error: PropTypes.shape({
    name: PropTypes.string.isRequired,
    message: PropTypes.string.isRequired
  }).isRequired
})

const tileType = PropTypes.oneOfType([loadedTileType, errorTileType]) // or null -- meaning "loading"

const tileRowOrGapType = PropTypes.oneOfType([
  PropTypes.number.isRequired,
  PropTypes.arrayOf(tileType).isRequired
])

export { tileType, tileRowOrGapType, columnDefinitionType }
