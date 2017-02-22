'use strict';

var ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
  entry: {
    'index': './index.styl',
    'index-no-normalize': './style/index.styl'
  },
  output: {
    filename: './dist/[name].css'
  },
  module: {
    loaders: [
      {
          test: /\.styl$/,
          loader: ExtractTextPlugin.extract('style-loader', 'css-loader!autoprefixer!stylus-loader')
      }
    ]
  },
  plugins: [
      new ExtractTextPlugin('./dist/[name].css')
  ]
}