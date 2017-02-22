'use strict'

var env = require('./env')

var PUBLIC = '/assets'

var entry     = require('./entry')
var plugins   = require('./plugins')
var loaders   = require('./loaders')
var externals = require('./externals')
var resolve   = require('./resolve')

module.exports = {
  entry: entry,
  output: {
    publicPath: PUBLIC
  },
  module: {
    loaders: loaders
  },
  externals: externals,
  resolve: resolve,
  plugins: plugins,

  devServer: {
      publicPath: PUBLIC,
      hot       : env.HOT,
      port      : env.PORT,
      historyApiFallback: true,
      info: true,
      quiet: false,

      stats: {
          colors: true,
          progress: true
      }
  }
}