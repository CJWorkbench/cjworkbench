var ExtractTextPlugin = require('extract-text-webpack-plugin')

module.exports = {
    entry: {
        'index': './index.styl'
    },
    output: {
        filename: 'index.css'
    },
    module: {
        loaders: [
            {
                test: /\.styl$/,
                loader: ExtractTextPlugin.extract('css-loader!stylus-loader')
            }
        ]
    },
    plugins: [
        new ExtractTextPlugin('[name].css')
    ]
}