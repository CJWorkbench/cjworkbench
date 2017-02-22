'use strict'

var webpack = require('webpack')
var assign  = require('object-assign')

var resolve   = require('./resolve')
var loaders   = require('./loaders')
var plugins   = require('./plugins')
var externals = assign({}, require('./externals'))

externals.react = 'React'

module.exports = {
    entry: './src/index.jsx',
    bail: true,
    output: {
        path         : __dirname + '/../dist',
        libraryTarget: 'umd',
        library      : 'ReactClass',
        filename     : 'index.js'
    },
    module: {
        loaders: loaders
    },
    externals: externals,
    resolve: resolve,
    plugins: plugins
}