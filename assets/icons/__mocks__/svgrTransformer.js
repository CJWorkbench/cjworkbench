// Transform an icon-SVG import into a component that looks good in a snapshot.
// https://jestjs.io/docs/en/webpack.html#mocking-css-modules
module.exports = {
  process (src, filename, config, options) {
    return `
      const React = require('react')

      module.exports = function SvgrMock (props) {
        return ${JSON.stringify(filename)}
      }
    `
  }
}
