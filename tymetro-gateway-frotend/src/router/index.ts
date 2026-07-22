import {
  createRouter,
  createWebHistory,
  createWebHashHistory,
} from "vue-router";
import type { RouteRecordRaw, Router } from "vue-router";
import { h, resolveComponent } from "vue";

const layoutMode = import.meta.env.VITE_LAYOUT_MODE;
const homeRedirect = layoutMode === '1-column-layout' ? 'mtr/train-list' : 'dashboard';

export const baseRoutes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "Layout",
    meta: { loading: true, requiresAuth: true },
    component: () => import("@/layouts/Layout/index.vue"),
    redirect: homeRedirect,
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/mtr/train-list.vue"),
        meta: { title: "Dashboard", affix: false, keepAlive: true, requiresAuth: false },
      },
      {
        path: "mtr",
        name: "mtr",
        component: { render: () => h(resolveComponent('router-view')) },
        children: [
          {
            path: "tile-menus",
            name: "tile-menus",
            component: () => import("@/views/mtr/tile-menus.vue"),
            meta: { title: "面板選單", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "parameters",
            name: "parameters",
            component: () => import("@/views/mtr/parameters.vue"),
            meta: { title: "參數設定", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "events",
            name: "events",
            component: () => import("@/views/mtr/events.vue"),
            meta: { title: "即時事件狀態", affix: false, keepAlive: true },
          },
          {
            path: "home",
            name: "mtr-home",
            component: () => import("@/views/mtr/home.vue"),
            meta: { title: "車廂狀態監控", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "period-settings",
            name: "period-settings",
            component: () => import("@/views/mtr/period-settings.vue"),
            meta: { title: "時段設定", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "schedule",
            name: "schedule",
            component: () => import("@/views/mtr/schedule.vue"),
            meta: { title: "排程設定", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "accounts",
            name: "accounts",
            component: () => import("@/views/mtr/accounts.vue"),
            meta: { title: "帳號資料", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "register-management",
            name: "register-management",
            component: () => import("@/views/mtr/register-management.vue"),
            meta: { title: "暫存器設定", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "audit-logs",
            name: "audit-logs",
            component: () => import("@/views/mtr/audit-logs.vue"),
            meta: { title: "審計日誌", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "train-list",
            name: "train-list",
            component: () => import("@/views/mtr/train-list.vue"),
            meta: { title: "車廂列表", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "single-end-pos/:carVin/:endPos",
            name: "single-end-pos",
            component: () => import("@/views/mtr/single-end-pos.vue"),
            meta: { title: "端點狀態監控", affix: false, keepAlive: false, requiresAuth: false },
          },
          {
            path: "history-records",
            name: "history-records",
            component: () => import("@/views/mtr/history-records.vue"),
            meta: { title: "歷史資料查詢", affix: false, keepAlive: true, requiresAuth: false },
          },
          {
            path: "sensor-map-config",
            name: "sensor-map-config",
            component: () => import("@/views/mtr/sensor-map-config.vue"),
            meta: { title: "感測器圖面配置", affix: false, keepAlive: true, requiresAuth: false },
          },
        ],
      },
      {
        path: "document-templates",
        name: "document-templates",
        component: () => import("@/views/base/document-templates.vue"),
        meta: { title: "樣板資料維護", affix: false, keepAlive: true },
      },
      {
        path: "organize-base/:id",
        name: "organize-base",
        component: () => import("@/views/base/form-base.vue"),
        props: true,
        meta: { title: "組織維護", affix: false, keepAlive: true, document: "organize-base" },
      },
      {
        path: "permission-records",
        name: "permission-records",
        component: () => import("@/views/base/record-base.vue"),
        meta: { title: "權限管理", affix: false, keepAlive: true },
      },
      {
        path: "visual-designer",
        name: "visual-designer",
        component: () => import("@/views/base/VisualDesigner.vue"),
        meta: { title: "JSON 設計器", affix: false, keepAlive: true },
      },
      {
        path: "equipment-page/:equipmentId/:endPos",
        name: "equipment-page",
        component: () => import("@/views/base/equipment-page.vue"),
        meta: { title: "車廂系統圖", affix: false, keepAlive: false },
      },
      {
        path: "car-page/:trainCode",
        name: "car-page",
        component: () => import("@/views/base/car-page.vue"),
        meta: { title: "列車監控", affix: false, keepAlive: true },
      },
      {
        path: "sensor-records-list",
        name: "sensor-records-list",
        component: () => import("@/views/base/sensor-records-list.vue"),
        meta: { title: "感測器紀錄", affix: false, keepAlive: true },
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("@/views/mtr/profile.vue"),
        meta: { title: "個人資料", affix: false, keepAlive: true },
      }
    ],
  },
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/Login.vue"),
    meta: { title: "Login" },
  },
  {
    path: "/mtr/home",
    name: "mtr-home-root",
    component: () => import("../views/mtr/home.vue"),
    meta: { title: "MRT HOME" },
  },
  // 404
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/NotFound.vue"),
    meta: { title: "Not Found" },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes: baseRoutes,
});

export default router;

// 全局導航守衛示範
// router.beforeEach((to, from, next) => {
//   console.log("導航到:", to.fullPath);
//   next();
// });
// const router = createRouter({
//   history: createWebHistory(),
//   strict: true,
//   routes: constantRoutes as RouteRecordRaw[],
// });
