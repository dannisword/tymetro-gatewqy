<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue?: boolean | number;
    disabled?: boolean;
    activeColor?: string;   // e.g. 'bg-rose-500'
    inactiveColor?: string; // e.g. 'bg-slate-300'
  }>(),
  {
    modelValue: false,
    disabled: false,
    activeColor: 'bg-primary-600',
    inactiveColor: 'bg-slate-300',
  }
);

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
}>();

const isOn = () => Boolean(props.modelValue);

const toggle = () => {
  if (!props.disabled) {
    emit('update:modelValue', !isOn());
  }
};
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="isOn()"
    :disabled="disabled"
    @click="toggle"
    :class="[
      'relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent',
      'transition-colors duration-200 ease-in-out',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500',
      'disabled:opacity-50 disabled:cursor-not-allowed',
      isOn() ? activeColor : inactiveColor,
    ]"
  >
    <span
      :class="[
        'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-md ring-0',
        'transition-transform duration-200 ease-in-out',
        isOn() ? 'translate-x-5' : 'translate-x-0',
      ]"
    />
  </button>
</template>
