const { defineConfig } = require("@vue/cli-service");

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      "/api": {
        // target: 'https://128.61.157.209/iot-backend',
        // target: "http://172.96.161.120:5000",
        // target: "http://127.0.0.1:5000",
        target: "http://10.2.192.220:5000",
        changeOrigin: true,
      },
    },
  },
  productionSourceMap: false,
});
