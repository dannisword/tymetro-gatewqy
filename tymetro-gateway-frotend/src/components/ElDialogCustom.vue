<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  title: { type: String, required: false },
  name: { type: String, required: false },
  cancel: { type: String, default: '取消', required: false },
  action: { type: String, default: '確認', required: false },
  showAction: { type: Boolean, default: true, required: false },
  width: { type: String, default: '50%', required: false },
  minHeight: { type: String, default: '300px', required: false },
})

const dialogRef = reactive({
  success: false,
  close: false,
  fullscreen: false,
  name: '',
})

watch(
  () => props.visible,
  (val) => {
    if (val) {
      activated()
    }
  },
)

const activated = async () => {
  dialogRef.fullscreen = props.width == '100%' ? true : false
  dialogRef.name = props.name == null ? '' : props.name
}

// event
const emit = defineEmits(['on-before-close', 'update:visible'])

const handleClose = (event: any) => {
  dialogRef.close = true
  emit('on-before-close', dialogRef)
}

const afterClosed = (val: boolean) => {
  dialogRef.success = val
  emit('on-before-close', dialogRef)
}
</script>

<template>
  <el-dialog
    :model-value="props.visible"
    :title="props.title"
    :width="props.width"
    :fullscreen="dialogRef.fullscreen"
    :before-close="handleClose"
    :close-on-click-modal="false"
    class="custom-dialog-wrapper"
    append-to-body
    destroy-on-close
  >
    <!-- 自定義標題提示（可選） -->
    <template #header>
      <div class="flex items-center gap-">
        <span class="w-1.5 h-6 bg-primary rounded-full"></span>
        <span class="text-lg font-bold text-slate-800 dark:text-slate-100">{{ props.title }}</span>
      </div>
    </template>

    <div class="dialog-content" :style="{ minHeight: props.minHeight }">
      <slot> </slot>
    </div>

    <template #footer v-if="showAction">
      <div class="flex justify-end gap-3 pt-2 pb-1">
        <el-button 
          @click="afterClosed(false)" 
          class="!px-6 !rounded-md hover:!bg-slate-50 transition-all"
        >
          {{ props.cancel }}
        </el-button>
        <el-button 
          type="primary" 
          @click="afterClosed(true)" 
          class="!px-8 !rounded-md shadow-lg shadow-primary/20 transition-all active:scale-95"
        >
          {{ props.action }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15) !important;
}

:deep(.el-dialog__header) {
  margin-right: 0;
  padding: 20px 24px;
  border-bottom: 1px solid #f1f5f9;
}

:deep(.dark .el-dialog__header) {
  border-bottom-color: #334155;
  background-color: #1e293b;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  background-color: #f8fafc;
  border-top: 1px solid #f1f5f9;
}

:deep(.dark .el-dialog__footer) {
  background-color: #1e293b;
  border-top-color: #334155;
}

.dialog-content {
  overflow: hidden;
  padding: 2px;
  display: flex;
  flex-direction: column;
}

/* RWD 適配 */
@media (max-width: 640px) {
  :deep(.el-dialog) {
    width: 95% !important;
  }
}
</style>
