<script setup lang="ts">
import { mdiTrain, mdiChevronRight } from "@mdi/js";
import BaseIcon from "@/components/BaseIcon.vue";

interface Car {
  id: number;
  carNo: string;
  carVin: string;
  status: string;
  lastUpdate: string;
}

interface Train {
  trainCode: string;
  carType: string;
  carTypeName: string;
  trainStatus: string;
  statusCounts: Record<string, number>;
  cars: Car[];
}

defineProps<{
  title: string;
  trains: Train[];
  type: 'EXPRESS' | 'COMMUTER';
}>();

defineEmits<{
  (e: 'click-train', trainCode: string): void;
}>();

const getStatusColor = (status: string) => {
  switch (status) {
    case 'OPERATING': return '#10B981';
    case 'MAINTENANCE': return '#F59E0B';
    case 'OFFLINE': return '#64748B';
    case 'ABNORMAL': return '#EF4444';
    default: return '#94A3B8';
  }
};
</script>

<template>
  <section v-if="trains.length > 0">
    <div class="flex items-center gap-3 mb-4 px-2">
      <h2 class="text-xl font-black text-slate-800 tracking-tight">
        {{ title }}
        <span class="ml-2 text-sm text-slate-400 font-bold">({{ trains.length }} 組)</span>
      </h2>
    </div>
    <div :class="[
      'grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
      type === 'EXPRESS' ? 'gap-4' : 'gap-3'
    ]">
      <div 
        v-for="train in trains" 
        :key="train.trainCode"
        @click="$emit('click-train', train.trainCode)"
        class="train-card bg-white rounded-xl p-3 border border-slate-100 shadow-sm hover:shadow-xl transition-all cursor-pointer group relative overflow-hidden flex flex-col"
      >
        <!-- Type Badge -->
        <div class="absolute top-0 right-0 px-1.5 py-0.5 text font-black text-white rounded-bl-md bg-blue-500">
          {{ type === 'EXPRESS' ? '直達' : '普通' }}
        </div>

        <!-- Card Header -->
        <div class="flex items-center gap-1.5 mb-2.5">
          <div :class="[
            'w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 shrink-0',
            type === 'EXPRESS' ? 'text-purple-800' : 'text-blue-800'
          ]">
            <BaseIcon :path="mdiTrain" size="16" />
          </div>
          <div class="min-w-0">
            <div class="text font-black text-slate-800 leading-none truncate">{{ train.trainCode }}</div>
            <div class="text-xs font-bold text-gray-500 mt-0.5 uppercase tracking-tighter truncate">{{ train.carTypeName }}</div>
          </div>
        </div>

        <!-- Cars Status (Train Silhouette Layout) -->
        <div class="flex items-center justify-center gap-0.5 mb-4 w-full max-w-[160px] mx-auto">
          <div 
            v-for="(car, index) in train.cars" 
            :key="car.id"
            class="h-7 flex-1 max-w-[32px] flex items-center justify-center border border-white shadow-sm transition-all hover:scale-105 hover:z-10 cursor-pointer"
            :class="[
              index === 0 ? 'rounded-l-lg' : '',
              index === train.cars.length - 1 ? 'rounded-r-lg' : ''
            ]"
            :style="{ backgroundColor: getStatusColor(car.status) }"
            :title="`車廂 ${car.carNo}`"
          >
            <span class="text-xs font-black text-white leading-none">{{ car.carNo }}</span>
          </div>
        </div>

        <!-- Footer Info -->
        <div class="flex justify-between items-center mt-auto pt-2 border-t border-slate-50">
          <div class="flex items-center gap-1">
            <div v-for="(count, status) in train.statusCounts" :key="status" class="flex items-center">
              <div class="w-3 h-3 rounded-full" :style="{ backgroundColor: getStatusColor(status) }"></div>
              <span class="text font-bold text-slate-400 ml-0.5">{{ count }}</span>
            </div>
          </div>
          <BaseIcon :path="mdiChevronRight" size="12" class="text-slate-300 group-hover:translate-x-0.5 transition-transform" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.train-card {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
</style>
