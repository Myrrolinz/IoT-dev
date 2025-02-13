const { defineConfig } = require("@vue/cli-service");

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    proxy: {
      "/api": {
        // target: "http://127.0.0.1:5000",
        target: "http://10.2.64.153:5000",
        changeOrigin: true,
      },
    },
  },
  productionSourceMap: false,
});
