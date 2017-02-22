module.exports = {
    entry: './index.jsx',
    output: {
        publicPath: 'http://localhost:9090/assets'
    },
    module: {
        loaders: require('./loaders.config')
    },
    externals: {
        'react': 'React'
    },
    resolve: {
        extensions: ['', '.js', '.jsx']
    }
}