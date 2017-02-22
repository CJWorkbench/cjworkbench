'use strict'

var webpack = require('webpack')

var resolve   = require('./resolve')
var externals = require('./externals')
var loaders   = require('./loaders')
var plugins   = require('./plugins')

var PUBLIC = '/assets'

module.exports = {
    entry: './index.jsx',
    output: {
        publicPath: PUBLIC
    },
    module: {
        loaders: loaders
    },
    externals: externals,
    resolve: resolve,
    plugins: [
        new webpack.HotModuleReplacementPlugin(),
        new webpack.NoErrorsPlugin()
    ].concat(plugins),
    devServer: {
        publicPath: PUBLIC
    }
}