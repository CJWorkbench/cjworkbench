'use strict';

var webpack = require('webpack')
var loaders = require('./loaders')
var plugins = require('./plugins')
var resolve = require('./resolve')
var externals = require('./externals')

externals.react = 'React'

module.exports = {
  entry: './src/index.jsx',
  output: {
    path         : __dirname + '/../dist',
    libraryTarget: 'umd',
    library      : 'DataGrid',
    filename     : 'react-datagrid.js'
  },
  module: {
    loaders: loaders
  },
  externals: externals,
  plugins: plugins,
  resolve: resolve
}