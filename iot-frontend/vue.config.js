const { defineConfig } = require("@vue/cli-service");

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      "/api": {
        target: "https://128.61.157.209/iot-backend",
        changeOrigin: true,
      },
    },
  },
  productionSourceMap: false,
});
