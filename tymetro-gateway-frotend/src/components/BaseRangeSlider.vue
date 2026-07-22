<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: number | null;
    min?: number;
    max?: number;
    step?: number;
    disabled?: boolean;
    minLabel?: string;
    maxLabel?: string;
    midLabel?: string;
  }>(),
  {
    modelValue: 24,
    min: 16,
    max: 30,
    step: 0.5,
    disabled: false,
    minLabel: '16.0°C',
    maxLabel: '30.0°C',
    midLabel: '舒適值 (24°C)',
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void;
  (e: 'change', value: number): void;
}>();

const onChange = (event: Event) => {
  const val = parseFloat((event.target as HTMLInputElement).value);
  emit('update:modelValue', val);
  emit('change', val);
};
</script>

<template>
  <div class="space-y-1">
    <input
      type="range"
      :min="min"
      :max="max"
      :step="step"
      :value="modelValue ?? min"
      :disabled="disabled"
      @change="onChange"
      class="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-600 disabled:opacity-50 disabled:cursor-not-allowed"
    />
    <div class="flex justify-between text-[10px] font-bold text-slate-400">
      <span>{{ minLabel }}</span>
      <span>{{ midLabel }}</span>
      <span>{{ maxLabel }}</span>
    </div>
  </div>
</template>
