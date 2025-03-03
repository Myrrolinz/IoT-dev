import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue"; // 替代 App.vue 的首页组件
import DeltaView from "../views/DeltaView.vue";
import MapAndChartsView from "../views/MapAndChartsView.vue";

const routes = [
  {
    path: "/",
    name: "Home",
    component: HomeView,
  },
  {
    path: "/delta",
    name: "DeltaView",
    component: DeltaView,
  },
  {
    path: "/maps",
    name: "MapAndChartsView",
    component: MapAndChartsView,
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

export default router;
