'use strict';

var ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
    entry: {
        'index': './index.styl',
        'index-no-normalize': './style/index.styl'
    },
    output: {
        filename: 'index.css'
    },
    module: {
        loaders: [
            {
                test: /\.styl$/,
                loader: ExtractTextPlugin.extract('style-loader', 'css-loader!stylus-loader')
            }
        ]
    },
    plugins: [
        new ExtractTextPlugin('[name].css')
    ]
}