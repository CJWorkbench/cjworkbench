'use strict'

var webpack = require('webpack')

module.exports = {
    entry: [
        './index.jsx'
    ],
    output: {
        publicPath: 'http://localhost:9090/assets'
    },
    module: {
        loaders: require('./loaders.config')
    },
    resolve: {
        extensions: ['', '.js', '.jsx']
    }
}