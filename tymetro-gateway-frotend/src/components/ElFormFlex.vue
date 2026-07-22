<script setup lang="ts">
import { PropType, ref } from "vue";
import { validEmpty } from "../utils";

const props = defineProps({
  schemas: { type: Array as PropType<any[]>, default: () => [] },
  model: { type: Object as PropType<any>, default: () => ({}) },
  labelWidth: { type: String, default: "auto" },
  gutter: { type: Number, default: 20 },
  isReadonly: { type: Boolean, default: false }
});

const formRef = ref();

/**
 * 核心驗證邏輯
 */
function validate(): Promise<boolean> {
  return new Promise((resolve) => {
    let hasError = false;
    for (let prop of props.schemas as any[]) {
      if (prop.rules && prop.rules.length > 0 && prop.rules[0].required) {
        // 從 model 中取當前值進行驗證
        const val = props.model[prop.prop];
        const isEmpty = validEmpty(val);
        
        if (isEmpty) {
          prop.rules[0].message = prop.rules[1]?.message || "此欄位為必填";
          hasError = true;
        } else {
          prop.rules[0].message = "";
        }
      }
    }
    resolve(hasError);
  });
}

const updateSchemaValue = (schema: any) => {
  schema.value = props.model[schema.prop];
};

const emits = defineEmits(["change", "blur"]);

const onSelectChange = (schema: any) => {
  schema.value = props.model[schema.prop];
  emits("change", schema);
};

const onBlur = (schema: any) => {
  schema.value = props.model[schema.prop];
  emits("blur", schema);
};

defineExpose({ validate });
</script>

<template>
  <el-form 
    ref="formRef" 
    :model="props.model"
    :label-width="props.labelWidth" 
    class="flex-form"
  >
    <el-row :gutter="props.gutter">
      <el-col 
        v-for="schema in props.schemas" 
        :key="schema.prop"
        :xs="24" 
        :sm="schema.sm || (schema.col > 12 ? 24 : 12)"
        :md="schema.md || schema.col || 12"
        :lg="schema.lg || schema.col || 12"
        :span="schema.col || 12"
        :class="['form-col', schema.class]"
      >
        <el-form-item
          :label="schema.label"
          :rules="schema.rules"
          :error="schema.rules && schema.rules.length > 0 ? schema.rules[0].message : ''"
          class="custom-form-item"
        >
          <!-- Textarea -->
          <el-input
            v-if="schema.type == 'textarea'"
            v-model="props.model[schema.prop]"
            @input="updateSchemaValue(schema)"
            type="textarea"
            :rows="schema.rows || 3"
            :placeholder="schema.placeholder || '請輸入內容'"
            :disabled="schema.disabled || props.isReadonly"
          />

          <!-- Select -->
          <el-select
            v-else-if="schema.type == 'select'"
            v-model="props.model[schema.prop]"
            class="w-full"
            :placeholder="schema.placeholder || '請選擇'"
            :disabled="schema.disabled || props.isReadonly"
            @change="onSelectChange(schema)"
            clearable
            filterable
          >
            <el-option
              v-for="option in schema.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>

          <!-- Number -->
          <el-input-number
            v-else-if="schema.type == 'number'"
            v-model="props.model[schema.prop]"
            @change="updateSchemaValue(schema)"
            class="!w-full"
            controls-position="right"
            :disabled="schema.disabled || props.isReadonly"
          />

          <!-- Date -->
          <el-date-picker
            v-else-if="schema.type == 'date'"
            v-model="props.model[schema.prop]"
            @change="updateSchemaValue(schema)"
            type="date"
            class="!w-full"
            value-format="YYYY-MM-DD"
            :disabled="schema.disabled || props.isReadonly"
          />

          <!-- Multiple Select -->
          <el-select
            v-else-if="schema.type == 'multiple-select'"
            v-model="props.model[schema.prop]"
            multiple
            class="w-full"
            :placeholder="schema.placeholder || '請選擇'"
            :disabled="schema.disabled || props.isReadonly"
            @change="onSelectChange(schema)"
            clearable
            filterable
          >
            <el-option
              v-for="option in schema.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>

          <!-- Autocomplete -->
          <el-autocomplete
            v-else-if="schema.type == 'autocomplete'"
            v-model="props.model[schema.prop]"
            :fetch-suggestions="(queryString: string, cb: any) => {
              const results = queryString
                ? schema.options.filter((o: any) => 
                    String(o.label || o.value).toLowerCase().includes(queryString.toLowerCase())
                  )
                : schema.options;
              cb(results.map((r: any) => ({ ...r, value: r.label || r.value })));
            }"
            class="w-full"
            :placeholder="schema.placeholder || '請輸入並選擇'"
            :disabled="schema.disabled || props.isReadonly"
            @select="onSelectChange(schema)"
            @input="updateSchemaValue(schema)"
            clearable
          />

          <!-- Default Input -->
          <el-input
            v-else
            v-model="props.model[schema.prop]"
            @input="updateSchemaValue(schema)"
            :placeholder="schema.placeholder || '請輸入'"
            :disabled="schema.disabled || props.isReadonly"
            @blur="onBlur(schema)"
          />
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>

<style scoped>
.flex-form {
  padding: 8px 0;
}

.custom-form-item {
  margin-bottom: 22px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #475569;
  padding-right: 12px;
}

:deep(.el-input__wrapper),
:deep(.el-textarea__inner) {
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  border-radius: 6px;
  transition: all 0.2s;
}

:deep(.el-input__wrapper.is-focus),
:deep(.el-textarea__inner:focus) {
  box-shadow: 0 0 0 1px var(--el-color-primary) inset !important;
}

.w-full {
  width: 100%;
}
</style>
