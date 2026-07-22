<script setup lang="ts">
import { ref, computed, reactive, onMounted, onUnmounted, nextTick, watch } from "vue";
import roomSvg from "@/assets/floor-all.svg";

// 定義病患資料格式
export interface Patient {
  id: string;
  name: string;
  age?: number;
  note?: string;
}

// 定義單張床位的資料格式
export interface BedConfig {
  id: string;
  label: string;
  type: "aerobic" | "normal";
  floor: "1F" | "2F" | string; // 放寬型別限制，讓動態樓層支援更佳
  patient?: Patient;
}

// 定義外部傳入的屬性與往外送出的事件
const props = withDefaults(defineProps<{ beds?: BedConfig[] }>(), {
  beds: () => []
});
const emit = defineEmits<{ (e: "select-bed", bed: BedConfig): void }>();

// SVG 原始畫布尺寸，用來計算縮放比例 (從 floor-all.svg viewBox 獲取正確值)
const SVG_W = 3718;
const SVG_H = 2381;

// 定義過濾器的型別
type FloorFilter = "all" | string;
type TypeFilter = "all" | "aerobic" | "normal";
type StatusFilter = "all" | "occupied" | "empty";

// 紀錄目前的過濾條件狀態
const currentFloor = ref<FloorFilter>("all");
const currentType = ref<TypeFilter>("all");
const currentStatus = ref<StatusFilter>("all");

// 下拉選單開關狀態
const floorMenuOpen = ref(false);
const typeMenuOpen = ref(false);

// 關閉下拉選單
const closeDropdowns = () => {
  floorMenuOpen.value = false;
  typeMenuOpen.value = false;
};

// 床位資訊
const activeBeds = computed(() => props.beds);

// 動態從資料中提取所有可選樓層陣列
const availableFloors = computed(() => [...new Set(activeBeds.value.map(bed => bed.floor))]);

// 點擊事件：選擇特定樓層
const selectFloor = (floor: FloorFilter) => {
  currentFloor.value = floor;
  closeDropdowns();
};

// 點擊事件：選擇特定類型
const selectType = (type: TypeFilter) => {
  currentType.value = type;
  closeDropdowns();
};

// 依據當前選擇的條件，計算出畫面上實體的床位
const visibleBeds = computed(() => {
  return activeBeds.value.filter(bed => {
    // 判斷樓層與類型
    const matchFloor = currentFloor.value === "all" || bed.floor === currentFloor.value;
    const matchType = currentType.value === "all" || bed.type === currentType.value;

    // 判斷是否有住民
    const hasPatient = !!(bed.patient && bed.patient.id);
    let matchStatus = true;
    if (currentStatus.value === "occupied") {
      matchStatus = hasPatient;
    }
    else if (currentStatus.value === "empty") {
      matchStatus = !hasPatient;
    }

    return matchFloor && matchType && matchStatus;
  });
});

// 將畫面上可見的「有住民床位」，依照樓層分組 (供右側總覽卡片使用)
const patientListByFloor = computed(() => {
  const grouped: Record<string, BedConfig[]> = {};

  visibleBeds.value.forEach(bed => {
    // 只抓有病患資料的床位
    if (bed.patient && bed.patient.id) {
      if (!grouped[bed.floor]) {
        grouped[bed.floor] = [];
      }
      grouped[bed.floor].push(bed);
    }
  });

  // 將樓層排序 (確保 1F 在 2F 前面)
  return Object.keys(grouped).sort().reduce((acc, key) => {
    acc[key] = grouped[key];
    return acc;
  }, {} as Record<string, BedConfig[]>);
});

// 紀錄目前被點擊選中的床位資料
const selectedBed = ref<BedConfig | null>(null);

// 存放 SVG 字串內容與外層容器的參考
const svgContent = ref("");
const svgContainer = ref<HTMLElement | null>(null);

// 紀錄每張床的中心點座標，用來繪製上方的小圓點與文字
const bedCoords = ref<Record<string, any>>({});

// 紀錄每層樓的定位座標，用來繪製樓層小標籤
const floorCoords = ref<Record<string, any>>({});

// 負責載入 SVG 檔案並初始化座標計算
const initSvgCoords = async () => {
  try {
    const res = await fetch(roomSvg);
    let text = await res.text();
    svgContent.value = text;
    await nextTick();

    if (!svgContainer.value) {
      return;
    }

    // 1. 巡覽所有床位資料，計算中心點 (cx, cy)
    const coords: any = {};
    activeBeds.value.forEach((bed) => {
      const el = svgContainer.value?.querySelector(`#${bed.id}`) as SVGGraphicsElement;
      if (el && typeof el.getBBox === "function") {
        const bbox = el.getBBox();
        console.log('bbox', bbox);

        coords[bed.id] = {
          cx: bbox.x + bbox.width / 2,
          cy: bbox.y + bbox.height / 2,
          bbox: bbox
        };
      }
    });
    bedCoords.value = coords;

    // 2. 計算樓層標籤座標：抓取整層樓 (#floor-1, #floor-2) 的群組邊界
    const fCoords: any = {};
    const floors = [...new Set(activeBeds.value.map(bed => bed.floor))];

    floors.forEach(floorName => {
      const floorNumber = floorName.replace("F", "");
      const el = svgContainer.value?.querySelector(`#floor-${floorNumber}`) as SVGGraphicsElement;

      if (el && typeof el.getBBox === "function") {
        const bbox = el.getBBox();

        // 動態計算座標，不用硬編碼值，樓層標籤放在右上角
        const labelX = bbox.x + bbox.width - 80;  // 距右邊緣 80px
        const labelY = bbox.y + 300;                // 距上邊緣 40px

        fCoords[floorName] = {
          x: labelX,
          y: labelY,
          bbox: bbox  // 保存 bbox 供參考
        };
      }
    });
    floorCoords.value = fCoords;

    // 座標算完後，執行一次圖層狀態更新
    updateSvgLayers();
  } catch (error) {
    console.error("SVG 載入失敗:", error);
  }
};

// 座標驗證函數，用於確認點擊是否真的在床位上
const isClickWithinBed = (clickX: number, clickY: number, bedId: string): boolean => {
  const bedCoord = bedCoords.value[bedId];
  if (!bedCoord || !bedCoord.bbox) {
    return false;
  }

  const bbox = bedCoord.bbox;
  // 檢查點擊座標是否在床位的邊界框內
  return (
    clickX >= bbox.x &&
    clickX <= bbox.x + bbox.width &&
    clickY >= bbox.y &&
    clickY <= bbox.y + bbox.height
  );
};

// 負責控制 SVG 內部圖層的顯示、隱藏與透明度
const updateSvgLayers = () => {
  if (!svgContainer.value) {
    return;
  }

  // 取得現有資料包含的樓層，並控制整層樓的顯示或隱藏
  availableFloors.value.forEach(floorName => {
    const floorNumber = floorName.replace("F", "");
    const floorGroup = svgContainer.value?.querySelector(`#floor-${floorNumber}`) as HTMLElement | null;

    if (floorGroup) {
      const isVisible = currentFloor.value === "all" || currentFloor.value === floorName;
      floorGroup.style.display = isVisible ? "block" : "none";
    }
  });

  // 控制每一張床位的狀態
  activeBeds.value.forEach((bed) => {
    const bedGroup = svgContainer.value?.querySelector(`#${bed.id}`) as HTMLElement;

    if (bedGroup) {
      // 抓取床位內部的各個狀態圖層
      const emptyLayer = bedGroup.querySelector(`#${bed.id}-empty`) as HTMLElement;
      const aerobicLayer = bedGroup.querySelector(`#${bed.id}-aerobic`) as HTMLElement;
      const normalLayer = bedGroup.querySelector(`#${bed.id}-normal`) as HTMLElement;
      const mainLayer = bedGroup.querySelector(`#${bed.id}-main`) as HTMLElement;

      // 將床體主結構放置於該群組最底層，避免遮擋狀態顏色
      if (mainLayer) {
        bedGroup.prepend(mainLayer);
      }

      const hasPatient = bed.patient && bed.patient.id;
      let targetLayer: HTMLElement | null = null;

      // 顯示哪一種床位圖層
      if (!hasPatient) {
        targetLayer = emptyLayer;
      } else if (bed.type === "aerobic") {
        targetLayer = aerobicLayer;
      } else {
        targetLayer = normalLayer;
      }

      [emptyLayer, aerobicLayer, normalLayer].forEach(layer => {
        if (layer) {
          layer.style.display = "none";
        }
      });

      // 將目標圖層顯示
      if (targetLayer) {
        targetLayer.style.display = "block";
        bedGroup.appendChild(targetLayer);
      }

      const isVisible = visibleBeds.value.some(b => b.id === bed.id);
      bedGroup.style.opacity = isVisible ? "1" : "0.15";
      bedGroup.style.cursor = isVisible ? "pointer" : "default";
      bedGroup.style.pointerEvents = isVisible ? "all" : "none";
    }
  });
};

watch([currentFloor, currentType, currentStatus], () => {
  nextTick(() => {
    updateSvgLayers();
  });
});

watch(activeBeds, () => {
  nextTick(() => {
    updateSvgLayers();
  });
});

// 拖曳與點擊邏輯
const view = reactive({ x: 0, y: 0, scale: 1 });
const viewportRef = ref<HTMLElement | null>(null);
const isPanning = ref(false);
let hasDragged = false;

// 初始縮放比例
const resizeMap = () => {
  const el = viewportRef.value;
  if (!el || el.clientWidth < 10) {
    return;
  }
  const W = el.clientWidth;
  const H = el.clientHeight;
  const margin = 16;
  const totalW = SVG_W + 48;
  const totalH = SVG_H + 48;
  const s = Math.min((W - margin * 2) / totalW, (H - margin * 2) / totalH);
  view.scale = Math.max(0.15, Math.min(4, s));
  view.x = (W - totalW * view.scale) / 2;
  view.y = (H - totalH * view.scale) / 2;
};

// Zoom in/out
const handleWheel = (e: WheelEvent) => {
  // 避免頁面跟著捲動
  e.preventDefault();

  // 第一步：標準化 delta
  // Mac Pinch 手勢或 Windows Ctrl+滾輪時
  const factor = e.ctrlKey ? 0.01 : 0.002;
  const zoomDelta = Math.exp(-e.deltaY * factor);

  const oldScale = view.scale;
  let nextScale = oldScale * zoomDelta;

  // 第二步：限制縮放範圍
  nextScale = Math.min(Math.max(nextScale, 0.15), 4);

  // 第三步：計算以滑鼠為中心的位移 (核心數學)
  // 取得滑鼠相對於容器的座標 (若是全螢幕可用 clientX/Y)
  const mouseX = e.clientX;
  const mouseY = e.clientY;

  // 計算縮放後的補償位移
  // 公式：新位移 = 滑鼠位置 - (滑鼠位置 - 舊位移) * (新倍率 / 舊倍率)
  const ratio = nextScale / oldScale;

  view.x = mouseX - (mouseX - view.x) * ratio;
  view.y = mouseY - (mouseY - view.y) * ratio;
  view.scale = nextScale;
};

// 開始拖曳地圖
const startPan = (e: MouseEvent) => {
  if (e.button === 0) {
    isPanning.value = true;
    hasDragged = false;
    e.preventDefault();
    closeDropdowns();
  }
};

// 拖曳地圖
const handleMapMouseMove = (e: MouseEvent) => {
  if (isPanning.value) {
    hasDragged = true;
    view.x += e.movementX;
    view.y += e.movementY;
  }
};

// 結束拖曳地圖
const endPan = () => isPanning.value = false;

// 床位點擊事件，更新選中狀態並向上拋出事件
const onBedClick = (bed: BedConfig) => {
  selectedBed.value = bed;
  emit("select-bed", bed);
};

// 關閉單一床位資訊面板，回到總覽模式
const closePanel = () => {
  selectedBed.value = null;
};

const handleSvgContainerClick = (e: MouseEvent) => {
  if (hasDragged) return;

  const target = e.target as Element;
  const bedGroup = target.closest('g[id*="bed"]');

  if (bedGroup) {
    // 先嘗試通過 ID 匹配
    const match = bedGroup.id.match(/f\d+-bed\d+/);
    if (match) {
      const baseBedId = match[0];
      const clickedBed = visibleBeds.value.find((b) => b.id === baseBedId);

      if (clickedBed) {
        // 驗證點擊座標確實在這個床位內
        if (svgContainer.value && svgContainer.value.getBoundingClientRect) {
          const rect = svgContainer.value.getBoundingClientRect();
          const clickX = (e.clientX - rect.left);
          const clickY = (e.clientY - rect.top);

          // 考慮縮放
          if (viewportRef.value) {
            // 計算相對於 SVG 原始座標的確切位置
            const scaledX = (clickX - view.x) / view.scale;
            const scaledY = (clickY - view.y) / view.scale;

            // 驗證座標在床位範圍內
            if (isClickWithinBed(scaledX, scaledY, baseBedId)) {
              e.stopPropagation();
              onBedClick(clickedBed);
              return;
            }
          }
        }

        // 備選方案：如果座標驗證失敗，但 ID 明確，仍然選中
        e.stopPropagation();
        onBedClick(clickedBed);
        return;
      }
    }
  }

  // 點擊空白處，取消選中單一床位
  closePanel();
};

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  initSvgCoords();
  nextTick(() => {
    if (viewportRef.value) {
      viewportRef.value.addEventListener("wheel", handleWheel, { passive: false });
      resizeObserver = new ResizeObserver(() => resizeMap());
      resizeObserver.observe(viewportRef.value);
      window.addEventListener("mouseup", endPan);
      resizeMap();
    }
  });
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  viewportRef.value?.removeEventListener("wheel", handleWheel);
  window.removeEventListener("mouseup", endPan);
});

// 決定小圓點顏色的邏輯
const dotColor = (bed: BedConfig) => {
  if (selectedBed.value?.id === bed.id) {
    return "#00ACC1";
  }
  if (bed.patient && bed.patient.id) {
    return "#688dc9";
  }
  return "#9CA3AF";
};
</script>

<template>
  <div class="flex flex-col gap-3 h-full" @click="closeDropdowns">
    <div class="flex flex-col gap-3 flex-shrink-0 p-2 z-20">

      <div class="flex items-center gap-3">

        <div class="relative">
          <button @click.stop="floorMenuOpen = !floorMenuOpen; typeMenuOpen = false"
            class="flex items-center py-2 px-3 bg-white rounded-lg shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 overflow-hidden hover:shadow-md transition-all h-9 gap-3">
            <div class="text-sm font-bold text-gray-500 tracking-widest flex items-center">
              樓層
            </div>
            <span class="text-gray-300 font-light font-sans scale-y-125">|</span>
            <div class="flex items-center gap-2 text-sm font-bold"
              :class="currentFloor === 'all' ? 'text-gray-500' : 'text-success-500 bg-slate-50 h-full'">
              {{ currentFloor === 'all' ? '全部' : currentFloor }}
            </div>
          </button>

          <Transition name="fade-down">
            <div v-if="floorMenuOpen"
              class="absolute top-full left-0 mt-2 w-32 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden py-1.5 flex flex-col z-30">
              <button @click.stop="selectFloor('all')"
                class="px-4 py-2.5 text-sm font-bold text-left transition-colors hover: bg-slate-50 hover:text-success-500"
                :class="currentFloor === 'all' ? 'text-success-500  bg-slate-50' : 'text-gray-600'">全部</button>

              <button v-for="floor in availableFloors" :key="floor" @click.stop="selectFloor(floor)"
                class="px-4 py-2.5 text-sm font-bold text-left transition-colors hover: bg-slate-50 hover:text-success-500"
                :class="currentFloor === floor ? 'text-success-500  bg-slate-50' : 'text-gray-600'">
                {{ floor }}
              </button>
            </div>
          </Transition>
        </div>

        <div class="relative">
          <button @click.stop="typeMenuOpen = !typeMenuOpen; floorMenuOpen = false"
            class="flex items-center py-2 px-3 bg-white rounded-lg shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 overflow-hidden hover:shadow-md transition-all h-9 gap-3">
            <div class="text-sm font-bold text-gray-500 tracking-widest flex items-center">
              類型
            </div>
            <span class="text-gray-300 font-light font-sans scale-y-125">|</span>
            <div class="flex items-center gap-2 text-sm font-bold"
              :class="currentType === 'all' ? 'text-gray-500' : 'text-success-500  bg-slate-50 h-full'">
              {{ currentType === 'all' ? '全部' : (currentType === 'aerobic' ? '有氧床' : '一般床') }}
            </div>
          </button>

          <Transition name="fade-down">
            <div v-if="typeMenuOpen"
              class="absolute top-full left-0 mt-2 w-32 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden py-1.5 flex flex-col z-30">
              <button @click.stop="selectType('all')"
                class="px-4 py-2.5 text-sm font-bold text-left transition-colors hover: bg-slate-50 hover:text-success-500"
                :class="currentType === 'all' ? 'text-success-500  bg-slate-50' : 'text-gray-600'">全部</button>
              <button @click.stop="selectType('aerobic')"
                class="px-4 py-2.5 text-sm font-bold text-left transition-colors hover: bg-slate-50 hover:text-success-500"
                :class="currentType === 'aerobic' ? 'text-success-500  bg-slate-50' : 'text-gray-600'">有氧床</button>
              <button @click.stop="selectType('normal')"
                class="px-4 py-2.5 text-sm font-bold text-left transition-colors hover: bg-slate-50 hover:text-success-500"
                :class="currentType === 'normal' ? 'text-success-500  bg-slate-50' : 'text-gray-600'">一般床</button>
            </div>
          </Transition>
        </div>

        <div
          class="inline-flex items-center bg-white rounded-lg shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 overflow-hidden w-max h-9 py-0 px-3">
          <div class="text-sm font-bold text-gray-500 tracking-widest flex items-center">
            床位資訊 <span class="text-gray-300 font-light font-sans scale-y-125 ml-2">|</span>
          </div>
          <button @click="currentStatus = 'all'"
            class="px-4 h-full text-sm font-medium transition-colors flex items-center gap-1.5"
            :class="currentStatus === 'all' ? 'bg-gray-100 text-gray-700' : 'text-gray-500 hover:bg-gray-50'">
            全部
          </button>

          <button @click="currentStatus = 'occupied'"
            class="px-4 h-full text-sm font-medium transition-colors flex items-center gap-1.5"
            :class="currentStatus === 'occupied' ? ' bg-slate-100' : 'text-gray-500 hover:bg-gray-50'">
            <span class="w-2.5 h-2.5 rounded-full bg-[#688dc9]"></span> 有住民
          </button>

          <button @click="currentStatus = 'empty'"
            class="px-4 h-full text-sm font-medium transition-colors flex items-center gap-1.5"
            :class="currentStatus === 'empty' ? 'bg-gray-100 text-gray-700' : 'text-gray-500 hover:bg-gray-50'">
            <span class="w-2.5 h-2.5 rounded-full border-[1.5px] border-gray-400"></span> 空床
          </button>




        </div>
      </div>
    </div>

    <div
      class="relative flex-1 min-h-0 flex flex-col overflow-hidden rounded-xl border border-gray-200 bg-[#f8f9fa] select-none shadow-inner">
      <div ref="viewportRef" class="flex-1 relative overflow-hidden"
        :class="isPanning ? 'cursor-grabbing' : 'cursor-grab'" @mousedown="startPan" @mousemove="handleMapMouseMove"
        @mouseleave="endPan">
        <div class="absolute origin-top-left p-6" :style="{
          transform: `translate(${view.x}px, ${view.y}px) scale(${view.scale})`,
        }">
          <div class="relative inline-block drop-shadow-xl" :style="{ width: `${SVG_W}px`, height: `${SVG_H}px` }">

            <div ref="svgContainer" class="absolute inset-0 block h-full w-full" @click="handleSvgContainerClick"
              v-html="svgContent"></div>

            <svg :viewBox="`0 0 ${SVG_W} ${SVG_H}`" class="relative z-[1] block h-full w-full"
              style="pointer-events: none" xmlns="http://www.w3.org/2000/svg">

              <template v-for="(coords, floorName) in floorCoords" :key="'label-' + floorName">
                <g v-if="currentFloor === 'all' || currentFloor === floorName"
                  :transform="`translate(${coords.x}, ${coords.y})`" style="opacity: 0.9;">
                  <rect x="0" y="0" width="60" height="32" rx="16" fill="#F3F4F6" stroke="#D1D5DB" stroke-width="1" />
                  <text x="30" y="17" text-anchor="middle" dominant-baseline="middle" font-size="18" font-weight="bold"
                    fill="#4B5563" style="user-select: none;">
                    {{ floorName }}
                  </text>
                </g>
              </template>

              <template v-for="bed in visibleBeds" :key="bed.id">
                <g v-if="bedCoords[bed.id]">
                  <circle :cx="bedCoords[bed.id].cx" :cy="bedCoords[bed.id].cy" r="18" :fill="dotColor(bed)"
                    fill-opacity="0.9" stroke="white" stroke-width="3" style="pointer-events: all; cursor: pointer"
                    @mousedown.stop @click.stop="onBedClick(bed)" />

                  <text :x="bedCoords[bed.id].cx" :y="bedCoords[bed.id].cy + 5" text-anchor="middle" font-size="14"
                    font-weight="bold" fill="white" style="pointer-events: none; user-select: none">
                    {{ bed.id.split("bed")[1] }}
                  </text>
                </g>
              </template>
            </svg>
          </div>
        </div>

        <div v-if="selectedBed || Object.keys(patientListByFloor).length > 0"
          class="absolute top-6 right-6 w-80 bg-white/95 backdrop-blur-sm rounded-xl shadow-lg border border-gray-200 z-20 flex flex-col max-h-[85%] overflow-hidden"
          @mousedown.stop @wheel.stop>

          <template v-if="selectedBed">
            <div
              class="px-5 py-4 border-b border-gray-100 bg-white flex justify-between items-center shrink-0 shadow-[0_2px_10px_rgba(0,0,0,0.03)] z-10 relative">
              <div class="flex items-center gap-2">
                <button @click="closePanel" class="text-gray-400 hover:text-success-500 transition-colors -ml-2">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
                  </svg>
                </button>
                <span class="font-bold text-gray-800 text-base tracking-wider">床位詳細資訊</span>
              </div>
              <span class="text-xs font-semibold px-3 py-1 rounded-full"
                :class="selectedBed.type === 'aerobic' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'">
                {{ selectedBed.type === "aerobic" ? "有氧床" : "一般床" }}
              </span>
            </div>

            <div class="overflow-y-auto overflow-x-hidden custom-scrollbar flex-1 min-h-0 bg-white">
              <div class="p-5 flex flex-col gap-4">
                <div class="flex items-end gap-1 mb-2">
                  <span class="text-xl font-black text-success-500 leading-none">{{ selectedBed.label }}</span>
                  <span class="text-sm font-bold text-gray-400">({{ selectedBed.floor }})</span>
                </div>

                <template v-if="selectedBed.patient">
                  <div class="space-y-3 text-sm bg-gray-50 p-4 rounded-lg border border-gray-100">
                    <div class="flex justify-between items-center">
                      <span class="text-gray-500 font-bold">姓名</span>
                      <span class="font-black text-gray-800 text-base">{{ selectedBed.patient.name }}</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-gray-500 font-bold">病歷號</span>
                      <span class="font-bold text-gray-700">{{ selectedBed.patient.id }}</span>
                    </div>
                    <div v-if="selectedBed.patient.age" class="flex justify-between items-center">
                      <span class="text-gray-500 font-bold">年齡</span>
                      <span class="font-bold text-gray-700">{{ selectedBed.patient.age }} 歲</span>
                    </div>
                    <div v-if="selectedBed.patient.note" class="flex flex-col gap-1 pt-2 mt-2 border-t border-gray-200">
                      <span class="text-gray-500 font-bold">備註</span>
                      <span class="font-medium text-gray-700 leading-relaxed">{{ selectedBed.patient.note }}</span>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="flex flex-col items-center justify-center py-8 text-gray-400 gap-2">
                    <span class="text-4xl opacity-50">🛏️</span>
                    <p class="text-sm font-bold mt-2">此床位目前無住民</p>
                  </div>
                </template>
              </div>
            </div>
          </template>

          <template v-else>
            <div
              class="px-5 py-4 border-b border-gray-100 bg-white flex justify-between items-center shrink-0 shadow-[0_2px_10px_rgba(0,0,0,0.03)] z-10 relative">
              <h3 class="font-bold text-gray-800 text-base tracking-wider">
                住民總覽
              </h3>
              <span class="text-xs  bg-slate-50 text-success-500 font-bold px-3 py-1 rounded-full">
                共 {{ Object.values(patientListByFloor).flat().length }} 床
              </span>
            </div>

            <div class="overflow-y-auto overflow-x-hidden custom-scrollbar flex-1 min-h-0 bg-white">
              <div class="p-5 flex flex-col gap-5">
                <template v-if="Object.keys(patientListByFloor).length > 0">
                  <div v-for="(beds, floor) in patientListByFloor" :key="floor">

                    <div class="flex items-center gap-3 mb-4 mt-1">
                      <span class="bg-gray-100 text-gray-700 text-sm font-black px-3 py-0.5 rounded-full shadow-sm">{{
                        floor }}</span>
                      <div class="h-px bg-gray-100 flex-1"></div>
                    </div>

                    <div class="flex flex-col gap-2">
                      <div v-for="bed in beds" :key="bed.id"
                        class="bg-white border border-gray-100 rounded-lg p-3 shadow-sm hover:border-success-500 hover:shadow-md cursor-pointer transition-all group"
                        @click="onBedClick(bed)">

                        <div class="flex items-center justify-between mb-1.5">
                          <span class="text-xs font-bold text-gray-400 group-hover:text-success-500 transition-colors">{{
                            bed.label }}</span>
                        </div>

                        <div class="text-sm font-medium tracking-wide flex items-center flex-wrap">
                          <span :class="bed.type === 'aerobic' ? 'text-yellow-600' : 'text-green-600'"
                            class="whitespace-nowrap">
                            {{ bed.type === 'aerobic' ? '有氧床' : '一般床' }}
                          </span>
                          <span class="text-gray-300 mx-2 font-light">|</span>
                          <span class="text-gray-800 font-bold whitespace-nowrap">{{ bed.patient?.name }}</span>
                          <span class="text-gray-300 mx-2 font-light">|</span>
                          <span class="text-gray-600 whitespace-nowrap">{{ bed.patient?.age }}歲</span>
                        </div>

                        <div class="text-xs text-gray-400 mt-2 pt-2 border-t border-gray-50 truncate"
                          :title="bed.patient?.note">
                          {{ bed.patient?.note }}
                        </div>

                      </div>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-down-enter-active,
.fade-down-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-down-enter-from,
.fade-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #E5E7EB;
  border-radius: 4px;
}

.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background: #D1D5DB;
}
</style>
