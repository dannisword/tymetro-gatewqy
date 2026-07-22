<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from "vue";
import type { CellStatus, MapCell, MapData } from "@/utils/types";

const props = defineProps<{ mapData: MapData }>();
const emit = defineEmits<{
  (e: "save", data: MapData): void;
  (e: "update:locationBase"): void;
  (e: "update:mapData", data: MapData): void;
}>();

// --- 2. 配置與常數 ---
const STATUS_CONFIG: Record<
  CellStatus,
  { label: string; bg: string; activeClass: string }
> = {
  0: {
    label: "空位",
    bg: "bg-white",
    activeClass: "bg-slate-700 text-white shadow-sm",
  },
  1: {
    label: "儲位",
    bg: "bg-emerald-500",
    activeClass: "bg-emerald-600 text-white shadow-sm",
  },
  2: {
    label: "軌道",
    bg: "bg-stone-400",
    activeClass: "bg-stone-600 text-white shadow-sm",
  },
  3: {
    label: "維修",
    bg: "bg-red-400",
    activeClass: "bg-red-600 text-white shadow-sm",
  },
  4: {
    label: "充電",
    bg: "bg-blue-400",
    activeClass: "bg-blue-600 text-white shadow-sm",
  },
};

// --- 3. 響應式狀態 ---
const levels = ref(1);
const currentLevel = ref(0);
const rows = ref(0);
const cols = ref(0);
const mapCells = ref<MapCell[][][]>([]);
const currentBrush = ref<CellStatus>(2);
const view = reactive({ x: 50, y: 80, scale: 0.8 });
const isDrawing = ref(false);
const select = reactive({
  active: false,
  startX: 0,
  startY: 0,
  endX: 0,
  endY: 0,
});
const selectedKeys = ref(new Set<string>());
let mapMetadata = reactive<Partial<MapData>>({});

// --- 4. Undo / Redo 邏輯 ---
const history = ref<string[]>([]);
const historyIndex = ref(-1);

const saveHistory = () => {
  const snapshot = JSON.stringify(mapCells.value);
  if (history.value[historyIndex.value] === snapshot) return;
  history.value = history.value.slice(0, historyIndex.value + 1);
  history.value.push(snapshot);
  if (history.value.length > 20) history.value.shift();
  else historyIndex.value++;
};

const undo = () => {
  if (historyIndex.value > 0) {
    historyIndex.value--;
    mapCells.value = JSON.parse(history.value[historyIndex.value]);
  }
};

const redo = () => {
  if (historyIndex.value < history.value.length - 1) {
    historyIndex.value++;
    mapCells.value = JSON.parse(history.value[historyIndex.value]);
  }
};

// --- 5. 核心初始化 ---
function initGrid() {
  const newL = levels.value || 1;
  const newR = rows.value || 12;
  const newC = cols.value || 12;
  const mapId = props.mapData.id || mapMetadata.id || null;
  const newCube: MapCell[][][] = [];

  for (let l = 0; l < newL; l++) {
    const rowArr: MapCell[][] = [];
    for (let r = 0; r < newR; r++) {
      const colArr: MapCell[] = [];
      for (let c = 0; c < newC; c++) {
        const old = mapCells.value[l]?.[r]?.[c];
        colArr.push(
          old
            ? old
            : ({
                id: null,
                mapId,
                rowIndex: r,
                colIndex: c,
                levelIndex: l,
                mapCellStatus: 0 as CellStatus,
                shelfId: null,
              } as MapCell),
        );
      }
      rowArr.push(colArr);
    }
    newCube.push(rowArr);
  }
  mapCells.value = newCube;
  saveHistory();
}

watch(
  () => props.mapData,
  (newV) => {
    if (newV?.mapCells) {
      levels.value = newV.levelNum || 1;
      rows.value = newV.rowCount || 0;
      cols.value = newV.colCount || 0;
      mapCells.value = JSON.parse(JSON.stringify(newV.mapCells));
      const { mapCells: _, ...meta } = newV;
      Object.assign(mapMetadata, meta);
      saveHistory();
    } else {
      initGrid();
    }
  },
  { immediate: true, deep: true },
);

// --- 6. 事件處理 ---
const handleGlobalMouseUp = () => {
  if (isDrawing.value || select.active) {
    if (select.active) {
      selectedKeys.value.forEach((key) => {
        const [r, c] = key.split("-").map(Number);
        if (mapCells.value[currentLevel.value]?.[r]?.[c])
          mapCells.value[currentLevel.value][r][c].mapCellStatus =
            currentBrush.value;
      });
    }
    saveHistory();
  }
  isDrawing.value = false;
  select.active = false;
  selectedKeys.value.clear();
};

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.ctrlKey && e.key === "z") {
    e.preventDefault();
    undo();
  }
  if (e.ctrlKey && (e.key === "y" || (e.shiftKey && e.key === "Z"))) {
    e.preventDefault();
    redo();
  }
};

onMounted(() => {
  window.addEventListener("mousemove", handleGlobalMouseMove);
  window.addEventListener("mouseup", handleGlobalMouseUp);
  window.addEventListener("keydown", handleKeyDown);
});

const handleExport = () => {
  const res = {
    ...mapMetadata,
    levelNum: levels.value,
    rowCount: rows.value,
    colCount: cols.value,
    mapCells: mapCells.value,
  };
  emit("save", res as MapData);
};

// --- 6. 交互邏輯 (平移、縮放、繪圖) ---
/**
 * 更新框選範圍並識別落入範圍內的格子
 * 邏輯：計算 DOM 元素的 BoundingClientRect 與框選矩形的交集
 */
const updateSelectionRange = () => {
  // 1. 計算框選矩形的四個邊界座標
  const rect = {
    l: Math.min(select.startX, select.endX),
    r: Math.max(select.startX, select.endX),
    t: Math.min(select.startY, select.endY),
    b: Math.max(select.startY, select.endY),
  };

  const newSet = new Set<string>();

  // 2. 遍歷畫面上所有的 grid-cell 元素
  document.querySelectorAll(".grid-cell").forEach((el) => {
    const b = el.getBoundingClientRect();

    // 3. 檢查元素的邊界是否與框選矩形重疊
    const isIntersecting = !(
      b.left > rect.r || // 元素在矩形右方
      b.right < rect.l || // 元素在矩形左方
      b.top > rect.b || // 元素在矩形下方
      b.bottom < rect.t // 元素在矩形上方
    );

    if (isIntersecting) {
      const r = el.getAttribute("data-r");
      const c = el.getAttribute("data-c");
      if (r && c) {
        // 將落入範圍的座標存入 Set，用於樣式顯示 (selectedKeys)
        newSet.add(`${r}-${c}`);
      }
    }
  });

  selectedKeys.value = newSet;
};
/**
 * 處理畫布縮放 (滑鼠滾輪)
 * Ctrl + 滾輪：精確縮放
 * 直接滾輪：垂直平移
 */
const handleWheel = (e: WheelEvent) => {
  if (e.ctrlKey) {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.95 : 1.05;
    view.scale = Math.min(Math.max(view.scale * delta, 0.1), 5);
  } else {
    // 若沒有按住 Ctrl，滾輪可用於垂直平移
    view.y -= e.deltaY;
  }
};

/**
 * 開始繪製或框選 (滑鼠按下)
 */
const startDrawing = (r: number, c: number, e: MouseEvent) => {
  // 僅響應左鍵 (button 0)
  if (e.button !== 0) return;

  if (e.altKey) {
    // 進入框選模式
    select.active = true;
    select.startX = select.endX = e.clientX;
    select.startY = select.endY = e.clientY;
  } else {
    // 進入直接繪圖模式
    isDrawing.value = true;
    if (mapCells.value[currentLevel.value]?.[r]?.[c]) {
      mapCells.value[currentLevel.value][r][c].mapCellStatus =
        currentBrush.value;
    }
  }
};

/**
 * 全域滑鼠移動處理
 * 1. Shift + 按住左鍵：平移畫布
 * 2. 框選模式：更新框選範圍
 * 3. 繪圖模式：偵測滑過路徑並塗色
 */
const handleGlobalMouseMove = (e: MouseEvent) => {
  // 畫布平移 (Shift + 左鍵拖拽)
  if (e.buttons === 1 && e.shiftKey) {
    view.x += e.movementX;
    view.y += e.movementY;
    return;
  }

  // 框選矩形更新
  if (select.active) {
    select.endX = e.clientX;
    select.endY = e.clientY;
    updateSelectionRange();
    return;
  }

  // 滑動繪圖
  if (isDrawing.value) {
    // 使用 elementFromPoint 偵測滑鼠下方的格子
    const el = document.elementFromPoint(e.clientX, e.clientY);
    const r = el?.getAttribute("data-r");
    const c = el?.getAttribute("data-c");

    if (r !== null && c !== null && r !== undefined && c !== undefined) {
      const rowIdx = Number(r);
      const colIdx = Number(c);

      // 確保目標格子存在於當前層
      if (mapCells.value[currentLevel.value]?.[rowIdx]?.[colIdx]) {
        // 優化：只有狀態不同時才更新，減少 Vue 渲染負擔
        if (
          mapCells.value[currentLevel.value][rowIdx][colIdx].mapCellStatus !==
          currentBrush.value
        ) {
          mapCells.value[currentLevel.value][rowIdx][colIdx].mapCellStatus =
            currentBrush.value;
        }
      }
    }
  }
};

const handleLocationBase = () => {
   emit("update:locationBase");
};
</script>

<template>
  <div
    class="relative w-full h-full overflow-hidden bg-slate-50 select-none"
    @wheel="handleWheel"
  >
    <div
      class="absolute w-full z-50 flex items-center gap-3 bg-white/90 backdrop-blur p-2 shadow-xl border border-slate-200"
    >
      <div class="flex gap-1 border-r pr-2">
        <button
          @click="undo"
          :disabled="historyIndex <= 0"
          class="p-1 disabled:opacity-20 hover:bg-slate-100 rounded"
        >
          撤銷
        </button>
        <button
          @click="redo"
          :disabled="historyIndex >= history.length - 1"
          class="p-1 disabled:opacity-20 hover:bg-slate-100 rounded"
        >
          重做
        </button>
      </div>
      <div class="flex items-center gap-2 text-xs font-bold">
        L
        <input
          v-model.number="levels"
          type="number"
          class="w-8 rounded"
          @change="initGrid"
        />
        R
        <input
          v-model.number="rows"
          type="number"
          class="w-8 rounded"
          @change="initGrid"
        />
        C
        <input
          v-model.number="cols"
          type="number"
          class="w-8 bg-slate-100 rounded"
          @change="initGrid"
        />
      </div>
      <select v-model="currentLevel" class="text-xs font-bold p-1 rounded">
        <option v-for="l in levels" :key="l - 1" :value="l - 1">
          第 {{ l }} 層
        </option>
      </select>
      <div class="flex gap-1">
        <button
          v-for="(conf, id) in STATUS_CONFIG"
          :key="id"
          @click="currentBrush = Number(id) as CellStatus"
          :class="[
            'flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all whitespace-nowrap',
            // 關鍵：如果當前刷子等於此 ID，套用 activeClass，否則透明
            currentBrush === Number(id)
              ? conf.activeClass
              : 'bg-transparent text-slate-500 hover:bg-slate-100',
          ]"
        >
          <div
            :class="['w-3 h-3 rounded-sm border border-black/5', conf.bg]"
          ></div>
          {{ conf.label }}
        </button>
      </div>
      <button
        @click="handleExport"
        class="px-5 py-2 bg-primary-600 text-white rounded-xl text-xs font-bold shadow-lg"
      >
        儲存
      </button>
      <button
        @click="handleLocationBase"
        class="px-5 py-2 bg-primary-600 text-white rounded-xl text-xs font-bold shadow-lg"
      >
        產生儲位
      </button>
    </div>

    <div
      class="absolute origin-top-left p-20"
      :style="{
        transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
      }"
    >
      <div class="inline-block bg-white shadow-2xl border border-slate-300">
        <div class="flex">
          <div
            class="w-8 h-8 bg-slate-50 border-b border-r border-slate-200"
          ></div>
          <div class="flex">
            <div
              v-for="c in cols"
              :key="'col-' + c"
              class="w-8 h-8 text-[9px] text-slate-400 flex items-center justify-center font-mono border-b border-slate-100 bg-slate-50"
            >
              {{ c - 1 }}
            </div>
          </div>
        </div>

        <div class="flex">
          <div class="flex flex-col">
            <div
              v-for="r in rows"
              :key="'row-' + r"
              class="w-8 h-8 text-[9px] text-slate-400 flex items-center justify-center font-mono border-r border-slate-100 bg-slate-50"
            >
              {{ r - 1 }}
            </div>
          </div>

          <div
            class="grid bg-slate-200 gap-[1px] shadow-inner"
            :style="{
              gridTemplateColumns: `repeat(${cols}, 32px)`,
              gridTemplateRows: `repeat(${rows}, 32px)`,
            }"
          >
            <template v-if="mapCells[currentLevel]">
              <template
                v-for="(rowArr, rIdx) in mapCells[currentLevel]"
                :key="'grid-row-' + rIdx"
              >
                <div
                  v-for="(cell, cIdx) in rowArr"
                  :key="'cell-' + rIdx + '-' + cIdx"
                  :data-r="rIdx"
                  :data-c="cIdx"
                  @mousedown.prevent="startDrawing(rIdx, cIdx, $event)"
                  class="grid-cell w-8 h-8 flex items-center justify-center relative transition-all duration-75"
                  :class="[
                    STATUS_CONFIG[cell.mapCellStatus].bg,
                    selectedKeys.has(`${rIdx}-${cIdx}`)
                      ? 'ring-2 ring-indigo-500 z-10 scale-90 opacity-80'
                      : '',
                  ]"
                >
                  <span
                    class="text-[7px] font-mono opacity-10 pointer-events-none"
                  >
                    {{ rIdx }},{{ cIdx }}
                  </span>
                </div>
              </template>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
