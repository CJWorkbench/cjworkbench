module.exports = [
    {
        test: /\.jsx$/,
        exclude: /node_modules/,
        loaders: [
            'babel-loader'
        ]
    },
    {
        test: /\.js$/,
        exclude: /node_modules/,
        loaders: [
            'babel-loader'
        ]
    },
    {
        test: /\.styl$/,
        loader: 'style-loader!css-loader!autoprefixer!stylus-loader'
    },
    {
        test: /\.css$/,
        loader: 'style-loader!css-loader!autoprefixer'
    }
]