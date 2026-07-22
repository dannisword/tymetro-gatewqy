<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
  GraphicComponent,
]);

// 1. 定義介面
interface Props {
  x: string[];
  seriesData: Record<string, number[]>; // { humidity: [...], temp: [...] }
  colorMap?: Record<string, string>;    // { humidity: '#ff0000' }
  dark?: boolean;
}

// 2. 統一 Props 宣告 (避免重複呼叫 defineProps)
const props = withDefaults(defineProps<Props>(), {
  colorMap: () => ({}),
  dark: false,
});

const el = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

// 預設顏色庫
const DEFAULT_COLORS = ["#60b000", "#2563eb", "#f59e0b", "#ef4444", "#8b5cf6"];

/**
 * 核心邏輯：取得標籤對應顏色
 */
const getTagColor = (tagName: string, index: number) => {
  return props.colorMap[tagName] || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
};

/**
 * 更新圖表配置
 */
const setOption = () => {
  if (!chart) return;

  const series = Object.entries(props.seriesData).map(([name, data], index) => {
    const color = getTagColor(name, index);
    
    return {
      name: name,
      type: "line",
      smooth: true,
      data: data,
      showSymbol: false,
      // 確保線條與圖例顏色一致
      itemStyle: { color: color },
      lineStyle: { width: 2, color: color },
      // 面積漸變效果
      areaStyle: {
        opacity: 0.1,
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color },
          { offset: 1, color: "transparent" },
        ]),
      },
    };
  });

  chart.setOption(
    {
      tooltip: {
        trigger: "axis",
        backgroundColor: props.dark ? "#1f2937" : "#fff",
        textStyle: { color: props.dark ? "#fff" : "#333" },
        borderColor: props.dark ? "#374151" : "#e5e7eb",
      },
      legend: {
        show: true,
        top: 10,
        textStyle: { color: props.dark ? "#ccc" : "#666" },
      },
      grid: { left: 40, right: 20, top: 50, bottom: 40 },
      xAxis: {
        type: "category",
        data: props.x,
        boundaryGap: false,
        axisLabel: { color: props.dark ? "#9ca3af" : "#6b7280" },
        axisLine: { lineStyle: { color: props.dark ? "#374151" : "#e5e7eb" } },
      },
      yAxis: {
        type: "value",
        splitLine: { lineStyle: { type: "dashed", opacity: props.dark ? 0.1 : 0.2 } },
        axisLabel: { color: props.dark ? "#9ca3af" : "#6b7280" },
      },
      series: series,
    },
    // 使用 notMerge: true 是為了防止當 series 數量減少時，舊的線條殘留在圖表上
    { notMerge: true }
  );
};

// --- Watchers ---

// A. 監控主題：需銷毀重建
watch(
  () => props.dark,
  (newDark) => {
    if (!el.value || !chart) return;
    chart.dispose();
    chart = echarts.init(el.value, newDark ? "dark" : undefined);
    setOption();
  }
);

// B. 監控數據與顏色映射：局部更新
watch(
  () => [props.x, props.seriesData, props.colorMap],
  () => setOption(),
  { deep: true }
);

onMounted(() => {
  if (!el.value) return;
  chart = echarts.init(el.value, props.dark ? "dark" : undefined);
  setOption();

  ro = new ResizeObserver(() => chart?.resize());
  ro.observe(el.value);
});

onBeforeUnmount(() => {
  ro?.disconnect();
  chart?.dispose();
});
</script>

<template>
  <div ref="el" class="w-full h-72 lg:h-80"></div>
</template>