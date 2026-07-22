import axios from 'axios'
import { useRoute } from 'vue-router'
import BaseHandle from './base-handle'
import httpOperations from '../utils/http-operations'
import { cloneDeep } from 'lodash'
import {
  getDocument,
  URLSearchParams,
  handleSearchData,
  objectToArray,
  getCacheOptions,
  arrayToObject,
  addDay,
} from '../utils'

import { AnySection } from '@/types/document-config'

export function DocumentHandle() {
  const route = useRoute()
  const instance = new BaseHandle()

  const loadJson = async () => {
    return new Promise((resolve, reject) => {
      const url = `json/${String(route.name)}.json`
      axios(url)
        .then((response: any) => {
          instance.map(response.data)
          resolve(response)
        })
        .catch((e) => {
          reject(e)
        })
    })
  }

  const loadDocument = async (document: string | undefined = undefined) => {
    return new Promise((resolve, reject) => {
      // 優先序：參數 > route.meta.document > route.name
      let component = (document || route.meta?.document || route.name)?.toString();

      if (!component) {
        console.error('[DocumentHandle] 無法確定要載入的 Document 名稱');
        return reject(false);
      }

      getDocument(component)
        .then((response: any) => {
          if (!response?.data?.content) {
            console.error(`[DocumentHandle] 找不到樣板內容: ${component}`);
            return reject(false);
          }
          const data = JSON.parse(response.data.content);
          instance.map(data);
          cleanSearch();
          resolve(true);
        })
        .catch((e) => {
          console.error(`[DocumentHandle] 載入樣板失敗: ${component}`, e);
          reject(false);
        });
    });
  }

  const cleanSearch = () => {
    const search = instance.sections.find((x: any) => x.sectionType === 'Search')
    // 下拉選單
    if (search) {
      instance.search.params = cloneDeep(search.params)
      objectToArray(instance.search.params, instance.search.schemas)
      searchChenge()
    }
  }

  const formCange = async () => {
    for (const schema of instance.form.schemas) {
      if (schema.type == 'select' || schema.type == 'multiple-select') {
        const data = getCacheOptions(schema.optionType)
        schema.options = data
      }
    }
  }

  const searchChenge = async () => {
    for (const schema of instance.search.schemas) {
      if (schema.type == 'select' || schema.type == 'multiple-select') {
        const data = getCacheOptions(schema.optionType)
        schema.options = data
      }

      // 預設值日期
      if (schema.type == 'date' && schema.isDefault == true) {
        if (schema.value) {
          schema.value.push(addDay(schema.start.day))
          schema.value.push(addDay(schema.end.day))
          // 處理時間
          handleSearchData(instance.search)
        } else {
          schema.value = []
        }
      }
    }
  }
  /**
   * 設定 form data
   * @param data
   */
  const setData = async (data: any) => {
    await formCange()
    const dto = await get(data.id)
    instance.form.dto = cloneDeep(dto)
    objectToArray(instance.form.dto, instance.form.schemas)
  }
  /**
   * 清除 form data
   */
  const cleanData = async () => {
    const form = instance.sections.find((x: any) => x.sectionType === 'Form')

    if (form) {
      await formCange()
      instance.form.dto = cloneDeep(form.dto)
      objectToArray(instance.form.dto, instance.form.schemas)
    }
  }

  const read = async (pagination: any = undefined) => {
    const url = instance.apiUrl.value.read
    if (!url) {
      console.warn('API路徑錯誤')
      return
    }

    // 同步搜尋條件：將畫面上 schemas 的值同步到 params 物件中
    arrayToObject(instance.search.params, instance.search.schemas)
    handleSearchData(instance.search)

    // 分頁設定
    if (pagination) {
      instance.search.params.pageIndex = pagination.page
      instance.search.params.pageSize = pagination.pageSize
    }

    const query = URLSearchParams(instance.search.params)
    const apiUrl = `${url}?${query}`
    await httpOperations
      .get(apiUrl)
      .then((response: any) => {
        const data = response.data;
        if (data && data.source) {
          instance.table.records = data.source
        }
        instance.pagination = data;
      })
      .catch((e) => {
        console.error('Error fetching records:', e)
      })
  }

  const get = async (id: number): Promise<any> => {
    const url = `${instance.apiUrl.value.read}/${id}`
    if (!url) {
      console.warn('API路徑錯誤')
      return null
    }
    try {
      const response = (await httpOperations.get(url)) as any
      return response?.data
    } catch (e) {
      console.error('Error fetching record:', e)
      return null
    }
  }

  const create = async (data: any) => {
    const url = instance.apiUrl.value.create
    if (!url) {
      console.warn('API路徑錯誤')
      return
    }
    if (!data) {
      console.warn('Data is not defined.')
      return
    }
    await httpOperations.post(url, data)
  }

  const update = async (data: any) => {
    const url = `${instance.apiUrl.value.update}/${data.id}`
    if (!url) {
      console.warn('Update URL is not defined.')
      return
    }
    if (!data) {
      console.warn('Data is not defined.')
      return
    }

    await httpOperations.put(url, data)
  }

  /**
   * 取得 section data
   * @param sections
   * @param type
   * @returns
   */
  const getSection = <T extends AnySection = AnySection>(
    sections: AnySection[],
    type: string,
    key?: string | undefined,
  ): T | undefined => {
    if (key) {
      return sections.find((x) => x.sectionType === type && x.key == key) as T | undefined
    }
    return sections.find((x) => x.sectionType === type) as T | undefined
  }

  return {
    instance,
    getSection,
    loadJson,
    loadDocument,
    cleanSearch,
    cleanData,
    setData,
    get,
    read,
    create,
    update,
  }
}
