<template>
  <div class="flex items-center px-4 py-2 hover:bg-gray-300 cursor-pointer">
    <span class="material-symbols-outlined mr-2">{{ icon }}</span>
    <span>{{ label }}</span>
  </div>
</template>

<script setup>
defineProps({
  icon: String,
  label: String
})
</script>
