<script setup lang="ts">
import { PropType, ref } from "vue";
import { validEmpty } from "../utils";

const props = defineProps({
  schemas: { type: Array as PropType<any[]> },
  colNum: { type: Number, default: 12 },
  cancel: { type: String, default: "取消", required: false },
  action: { type: String, default: "確認", required: false },
});
const formRef = ref();
const element = ref();

// event
const emits = defineEmits([
  "on-before-close",
  "on-form-btnClick",
  "on-select-change",
  "on-blur",
  "on-fetch",
  "on-suggestions",
]);
const setDisabled = (schema: any) => {
  return schema.disabled;
};

/**
 * auto complete fetch call back
 * @param val
 * @param cb
 */
const onFetch = (val: any, cb: (arg: any) => void) => {
  emits("on-fetch", element.value, cb);
};

const onSelected = (schema: any) => {
  emits("on-suggestions", schema);
};

const onFocus = (schema: any) => {
  // 設定 auto complete foc
  element.value = schema;
};

const onSelectChange = (schema: any) => {
  emits("on-select-change", schema);
};
/**
 * 離開輸入框
 * @param schema
 */
const onBlur = (schema: any) => {
  emits("on-blur", schema);
};
/**
 *
 * @param funcName
 */
const onFormBtnClick = async (schemas: any) => {
  emits("on-form-btnClick", schemas);
};
const schemas = async () => {
  return props.schemas;
};
function validate(): Promise<boolean> {
  return new Promise((resolve) => {
    let isValid = false;
    for (let prop of props.schemas as any[]) {
      // 確保 rules 存在且有內容
      if (prop.rules && prop.rules.length > 0 && prop.rules[0].required) {
        const valid = validEmpty(prop.value);
        if (valid) {
          prop.rules[0].message = prop.rules[1]?.message || "此欄位為必填";
        } else {
          prop.rules[0].message = "";
        }
        if (valid == true) {
          isValid = valid;
          resolve(isValid);
          break;
        }
      }
    }
    resolve(isValid);
  });
}

defineExpose({
  validate,
});
</script>

<template>
  <el-form ref="formRef" label-width="auto" :inline="false">
    <el-row :gutter="20">
      <el-col 
        :span="props.colNum" 
        v-for="schema in props.schemas"
        :key="schema.prop"
      >
        <el-form-item
          :label="schema.label"
          :rules="schema.rules"
          :error="schema.rules && schema.rules.length > 0 ? schema.rules[0].message : ''"
        >
          <!-- autocomplete -->
          <el-autocomplete
            v-if="schema.type == 'autocomplete'"
            v-model="schema.value"
            :disabled="setDisabled(schema)"
            :fetch-suggestions="onFetch"
            @select="onSelected"
            @focus="onFocus(schema)"
          >
            <template #default="{ item }">
              {{ item.value }}
            </template>
          </el-autocomplete>
          <!-- textarea -->
          <el-input
            v-if="schema.type == 'textarea'"
            v-model="schema.value"
            type="textarea"
            :disabled="setDisabled(schema)"
          ></el-input>
          <!-- multiple  select-->
          <el-select
            v-else-if="schema.type == 'multiple-select'"
            v-model="schema.value"
            placeholder="請選擇"
            multiple
            :disabled="setDisabled(schema)"
            clearable
            filterable
          >
            <el-option
              v-for="option in schema.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
            </el-option>
          </el-select>
          <!-- select -->
          <el-select
            v-else-if="schema.type == 'select'"
            v-model="schema.value"
            placeholder="請選擇"
            :disabled="setDisabled(schema)"
            @change="onSelectChange(schema)"
            clearable
            filterable
          >
            <el-option
              v-for="option in schema.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
            </el-option>
          </el-select>

          <el-select
            v-else-if="schema.type == 'fixed-select'"
            v-model="schema.value"
            placeholder="請選擇"
            :disabled="setDisabled(schema)"
            @change="onSelectChange(schema)"
            clearable
            filterable
          >
            <el-option
              v-for="option in schema.defaultOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
            </el-option>
          </el-select>

          <!-- select change-->
          <el-select
            v-else-if="schema.type == 'tigger-select'"
            v-model="schema.value"
            placeholder="請選擇"
            :disabled="setDisabled(schema)"
          >
            <el-option
              v-for="option in schema.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
            </el-option>
          </el-select>
          <!-- date -->
          <el-date-picker
            v-else-if="schema.type == 'date'"
            type="date"
            v-model="schema.value"
            style="width: 100%"
            value-format="YYYY-MM-DD"
            :disabled="setDisabled(schema)"
          ></el-date-picker>

          <!-- time-->
          <el-time-select
            v-else-if="schema.type == 'time'"
            v-model.lazy="schema.value"
            :start="schema.start"
            :end="schema.end"
            :step="schema.step"
            :disabled="setDisabled(schema)"
          ></el-time-select>
          <!-- checkbox-->
          <el-checkbox
            v-else-if="schema.type == 'checkbox'"
            v-model="schema.value"
            :disabled="setDisabled(schema)"
          />
          <!-- number-->
          <el-input
            v-else-if="schema.type == 'number'"
            v-model="schema.value"
            type="number"
            :disabled="setDisabled(schema)"
            @blur="onBlur(schema)"
            @keyup.enter.native="onBlur(schema)"
          ></el-input>
          <!-- radio-group -->
          <el-radio-group
            v-else-if="schema.type == 'radio-group'"
            v-model="schema.value"
            @change="onSelectChange(schema)"
          >
            <el-radio-button
              v-for="option in schema.options"
              :label="option.value"
            >
              {{ option.label }}
            </el-radio-button>
          </el-radio-group>
          <!-- text -->
          <el-input
            v-else-if="schema.type == 'input'"
            v-model="schema.value"
            :disabled="setDisabled(schema)"
            @blur="onBlur(schema)"
            @keyup.enter.native="onBlur(schema)"
          ></el-input>
          <!-- password -->
          <el-input
            v-else-if="schema.type == 'hidden-word'"
            v-model="schema.value"
            :disabled="schema.disabled"
            show-password
          ></el-input>
          <!-- button -->
          <el-button
            v-else-if="schema.type == 'button' && schema.mode == 'edit'"
            :type="schema.buttonType"
            :disabled="setDisabled(schema)"
            @click="onFormBtnClick(schema)"
            >{{ schema.value }}</el-button
          >
        </el-form-item>
      </el-col>
    </el-row>
  </el-form>
</template>
