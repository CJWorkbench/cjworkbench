'use strict';

var webpack = require('webpack')
var ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
  entry: {
    'index': './index.styl',
    'index-no-normalize': './style/index.styl'
  },
  output: {
    filename: './dist/[name].min.css'
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
    new ExtractTextPlugin('./dist/[name].min.css'),
    new webpack.optimize.UglifyJsPlugin()
  ]
}